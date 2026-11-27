import AVFoundation
import CallKit
import PushKit
import Speech
import Security
import SwiftUI
import UserNotifications

private struct Session: Decodable, Identifiable {
    let id: String
    let project: String
    var mode: String
}

private struct Question: Decodable, Identifiable {
    let id: String
    let prompt: String
}

private struct Batch: Decodable, Identifiable {
    let id: String
    let session: String
    let summary: String
    let state: String
    let questions: [Question]
}

private struct Event: Decodable, Identifiable {
    let id: String
    let seq: Int
    let session: String
    let kind: String
    let subject: String
    let detail: String?
}

private struct AnswerRow: Encodable {
    let question_id: String
    var action = "answer"
    var text = ""
}

private struct Submission: Encodable {
    let id: UUID
    let answers: [AnswerRow]
}

private struct AppError: LocalizedError {
    let errorDescription: String?
    init(_ description: String) { errorDescription = description }
}

private enum Credentials {
    static var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "ClaudeRemote",
         kSecAttrAccount as String: "dispatcher-token"]
    }

    static func load() -> String {
        var lookup = query
        lookup[kSecReturnData as String] = true
        var result: CFTypeRef?
        guard SecItemCopyMatching(lookup as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return "" }
        return String(decoding: data, as: UTF8.self)
    }

    static func save(_ token: String) throws {
        let data = Data(token.utf8)
        let attributes = [kSecValueData as String: data,
                          kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly] as [String: Any]
        var status = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if status == errSecItemNotFound {
            var entry = query
            entry[kSecValueData as String] = data
            entry[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            status = SecItemAdd(entry as CFDictionary, nil)
        }
        guard status == errSecSuccess else { throw AppError("Der Schlüsselbund konnte das Token nicht speichern.") }
    }
}

private final class NoRedirect: NSObject, URLSessionTaskDelegate {
    func urlSession(_ session: URLSession, task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

@MainActor
private final class Store: ObservableObject {
    @Published var url = UserDefaults.standard.string(forKey: "dispatcherURL") ?? ""
    @Published var token = Credentials.load()
    @Published var sessions: [Session] = []
    @Published var batches: [Batch] = []
    @Published var events: [Event] = []
    @Published var selected: Batch?
    @Published var problem: String?
    @Published var connected = false
    var pendingEvent: String?
    var deviceToken: String?
    private let transport = URLSession(configuration: .ephemeral, delegate: NoRedirect(), delegateQueue: nil)

    func request(_ path: String, method: String = "GET", body: Data? = nil) async throws -> Data {
        let trimmed = url.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let base = URLComponents(string: trimmed), base.scheme == "https", base.host != nil,
              base.user == nil, base.password == nil, base.query == nil, base.fragment == nil,
              let endpoint = URL(string: trimmed.trimmingCharacters(in: CharacterSet(charactersIn: "/")) +
                                 "/api/v1" + path) else { throw AppError("Gib eine gültige HTTPS-Adresse ein.") }
        var request = URLRequest(url: endpoint, timeoutInterval: 15)
        request.httpMethod = method
        request.httpBody = body
        request.setValue("Bearer " + token, forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await transport.data(for: request)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw AppError("Dispatcher-Anfrage fehlgeschlagen (HTTP \((response as? HTTPURLResponse)?.statusCode ?? 0)).")
        }
        return data
    }

    func fetch<T: Decodable>(_ path: String, as type: T.Type) async throws -> T {
        try JSONDecoder().decode(type, from: await request(path))
    }

    func reload() async throws {
        sessions = try await fetch("/sessions", as: [Session].self)
        batches = try await fetch("/question-batches", as: [Batch].self)
        var timeline: [Event] = []
        repeat {
            let page = try await fetch("/events?cursor=\(timeline.last?.seq ?? 0)", as: [Event].self)
            timeline += page
            if page.count < 100 { break }
        } while true
        events = Array(timeline.reversed())
    }

    func connect() async {
        do {
            try await reload()
            try Credentials.save(token)
            UserDefaults.standard.set(url, forKey: "dispatcherURL")
            connected = true
            if let pendingEvent { await open(pendingEvent) }
            if let deviceToken { await register(deviceToken) }
            #if DEBUG || TELEKLAUS_PERSONAL_CALLS
            Notifications.calls.startIfEnabled()
            await Notifications.calls.registerToken()
            #endif
        } catch { problem = error.localizedDescription }
    }

    func updateMode(_ session: Session) async {
        do {
            let next = session.mode == "autonomous" ? "interactive" : "autonomous"
            _ = try await request("/sessions/\(session.id)/mode", method: "PATCH",
                                  body: JSONEncoder().encode(["mode": next]))
            try await reload()
        } catch { problem = error.localizedDescription }
    }

    func open(_ id: String) async {
        pendingEvent = id
        guard connected, UUID(uuidString: id) != nil else { return }
        do {
            let event = try await fetch("/events/\(id)", as: Event.self)
            try await reload()
            if event.kind == "question" {
                selected = try await fetch("/question-batches/\(event.subject)", as: Batch.self)
            }
            pendingEvent = nil
        } catch { problem = error.localizedDescription }
    }

    func register(_ value: String) async {
        deviceToken = value
        guard connected else { return }
        do {
            _ = try await request("/devices/register", method: "POST",
                                  body: JSONEncoder().encode(["token": value, "environment": apnsEnvironment]))
        } catch { problem = error.localizedDescription }
    }
}

/// APNs environment of this build for the dispatcher: "sandbox" (Debug) or "production" (Release).
let apnsEnvironment: String = {
    let value = Bundle.main.object(forInfoDictionaryKey: "TeleKlausAPSEnvironment") as? String
    return value == "development" ? "sandbox" : "production"
}()

private final class Notifications: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    static let store = Store()
    #if DEBUG || TELEKLAUS_PERSONAL_CALLS
    static let calls = VoiceCalls()
    #endif

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        #if DEBUG || TELEKLAUS_PERSONAL_CALLS
        Self.calls.startIfEnabled()
        #endif
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let value = deviceToken.map { String(format: "%02x", $0) }.joined()
        Task { await Self.store.register(value) }
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter,
                                didReceive response: UNNotificationResponse) async {
        if let id = response.notification.request.content.userInfo["event_id"] as? String {
            await Self.store.open(id)
        }
    }
}

@main
struct ClaudeRemoteApp: App {
    @UIApplicationDelegateAdaptor(Notifications.self) private var notifications

    var body: some Scene {
        WindowGroup { Home(store: Notifications.store) }
    }
}

private struct Home: View {
    @ObservedObject var store: Store

    var body: some View {
        NavigationStack {
            List {
                #if DEBUG || TELEKLAUS_PERSONAL_CALLS
                Button("Sprachanrufe aktivieren") {
                    Task {
                        do { try await Notifications.calls.enable() }
                        catch { store.problem = error.localizedDescription }
                    }
                }
                #endif
                if store.connected {
                    Section("Sitzungen") {
                        ForEach(store.sessions) { session in
                            Button {
                                Task { await store.updateMode(session) }
                            } label: {
                                LabeledContent(session.project, value: session.mode == "autonomous" ? "Autonom" : "Interaktiv")
                            }
                        }
                    }
                    Section("Fragen") {
                        ForEach(store.batches) { batch in
                            Button(batch.summary) { store.selected = batch }
                        }
                    }
                    Section("Verlauf") {
                        ForEach(store.events) { event in
                            LabeledContent(event.kind, value: store.sessions.first { $0.id == event.session }?.project ?? event.session)
                        }
                    }
                    Button("Mitteilungen aktivieren") {
                        Task {
                            do {
                                if try await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) {
                                    UIApplication.shared.registerForRemoteNotifications()
                                }
                            } catch { store.problem = error.localizedDescription }
                        }
                    }
                    Button("Verbindung bearbeiten") { store.connected = false }
                } else {
                    Section("Dispatcher") {
                        TextField("HTTPS-Adresse", text: $store.url)
                            .keyboardType(.URL).textInputAutocapitalization(.never).autocorrectionDisabled()
                        SecureField("Zugangstoken", text: $store.token)
                        Button("Verbinden") { Task { await store.connect() } }
                    }
                }
                if let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String {
                    Text("Build \(build)")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("TeleKlaus")
            #if DEBUG
            .toolbar {
                if ProcessInfo.processInfo.arguments.contains("-TeleKlausVoiceTest") {
                    Button("Sprachtest") {
                        Task {
                            do { try await Notifications.calls.preview() }
                            catch is CancellationError {}
                            catch { store.problem = error.localizedDescription }
                        }
                    }
                }
            }
            #endif
            .refreshable {
                if store.connected {
                    do { try await store.reload() } catch { store.problem = error.localizedDescription }
                }
            }
            .sheet(item: $store.selected) { AnswerSheet(store: store, batch: $0) }
            .alert("TeleKlaus", isPresented: Binding(
                get: { store.problem != nil }, set: { if !$0 { store.problem = nil } }
            )) {
                Button("OK") { store.problem = nil }
            } message: { Text(store.problem ?? "") }
            .task {
                if !store.url.isEmpty && !store.token.isEmpty { await store.connect() }
                if await UNUserNotificationCenter.current().notificationSettings().authorizationStatus == .authorized {
                    UIApplication.shared.registerForRemoteNotifications()
                }
            }
        }
    }
}

private struct AnswerSheet: View {
    @Environment(\.dismiss) private var dismiss
    @ObservedObject var store: Store
    let batch: Batch
    @State private var answers: [AnswerRow]
    @State private var submission: Submission?
    @State private var sending = false
    @State private var error: String?

    init(store: Store, batch: Batch) {
        self.store = store
        self.batch = batch
        _answers = State(initialValue: batch.questions.map { AnswerRow(question_id: $0.id) })
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(batch.summary)
                    if batch.state != "open" { Text(batch.state == "pending" ? "Wartet auf Bestätigung" : "Bestätigt") }
                }
                ForEach(answers.indices, id: \.self) { index in
                    Section(batch.questions[index].prompt) {
                        if batch.state == "open" {
                            Picker("Entscheidung", selection: $answers[index].action) {
                                Text("Antworten").tag("answer")
                                Text("Freigeben").tag("approve")
                                Text("Ablehnen").tag("decline")
                            }
                            if answers[index].action == "answer" {
                                TextField("Antwort", text: $answers[index].text)
                            }
                        }
                    }
                    .disabled(submission != nil)
                }
                if batch.state == "open" {
                    Button("Entscheidung senden") { Task { await submit() } }
                        .disabled(sending || answers.contains { $0.action == "answer" && $0.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty })
                }
                if let error { Text(error).foregroundStyle(.red) }
            }
            .navigationTitle("Fragebatch")
            .toolbar { Button("Schließen") { dismiss() } }
        }
    }

    private func submit() async {
        sending = true
        defer { sending = false }
        let envelope = submission ?? Submission(id: UUID(), answers: answers)
        submission = envelope
        do {
            _ = try await store.request("/question-batches/\(batch.id)/answers", method: "POST",
                                        body: JSONEncoder().encode(envelope))
        } catch {
            self.error = error.localizedDescription
            return
        }
        do { try await store.reload() } catch { store.problem = error.localizedDescription }
        dismiss()
    }
}

#if DEBUG || TELEKLAUS_PERSONAL_CALLS
@MainActor
private final class VoiceCalls: NSObject, PKPushRegistryDelegate, CXProviderDelegate {
    private let provider: CXProvider
    private var registry: PKPushRegistry?
    private var token: String?
    private var callID: UUID?
    private var content: Task<CallContent, Error>?
    private var connection: Store?
    private var conversation: Task<Void, Never>?
    private var answered = false
    private var voice: GermanVoice?
    private var previewing = false
    private let enabledKey = "voiceCallsEnabled"

    private struct CallContent {
        let project: String
        let batch: Batch?
    }

    override init() {
        let configuration = CXProviderConfiguration()
        configuration.supportedHandleTypes = [.generic]
        configuration.maximumCallGroups = 1
        configuration.maximumCallsPerCallGroup = 1
        configuration.includesCallsInRecents = false
        provider = CXProvider(configuration: configuration)
        super.init()
        provider.setDelegate(self, queue: .main)
    }

    func enable() async throws {
        try await GermanVoice.authorize()
        UserDefaults.standard.set(true, forKey: enabledKey)
        startIfEnabled()
        await registerToken()
    }

    func startIfEnabled() {
        #if !targetEnvironment(simulator)
        guard registry == nil, UserDefaults.standard.bool(forKey: enabledKey) else { return }
        let registry = PKPushRegistry(queue: .main)
        registry.delegate = self
        self.registry = registry
        registry.desiredPushTypes = [.voIP]
        #endif
    }

    func registerToken() async {
        guard let token else { return }
        let connection = Store()
        guard !connection.url.isEmpty, !connection.token.isEmpty else { return }
        do {
            _ = try await connection.request("/devices/register", method: "POST",
                body: JSONEncoder().encode(["token": token, "kind": "voip", "environment": apnsEnvironment]))
        } catch {
            Notifications.store.problem = error.localizedDescription
        }
    }

    // Both delegates are registered on the main queue.
    nonisolated func pushRegistry(_ registry: PKPushRegistry, didUpdate credentials: PKPushCredentials, for type: PKPushType) {
        MainActor.assumeIsolated {
            guard type == .voIP else { return }
            token = credentials.token.map { String(format: "%02x", $0) }.joined()
            Task { await registerToken() }
        }
    }

    nonisolated func pushRegistry(_ registry: PKPushRegistry, didInvalidatePushTokenFor type: PKPushType) {
        MainActor.assumeIsolated {
            if type == .voIP { token = nil }
        }
    }

    nonisolated func pushRegistry(_ registry: PKPushRegistry, didReceiveIncomingPushWith payload: PKPushPayload,
                      for type: PKPushType, completion: @escaping () -> Void) {
        MainActor.assumeIsolated {
            guard type == .voIP else { completion(); return }
            let eventID = (payload.dictionaryPayload["event_id"] as? String).flatMap(UUID.init(uuidString:))
            let incomingID = eventID ?? UUID()
            let update = CXCallUpdate()
            update.remoteHandle = CXHandle(type: .generic, value: "Claude")
            update.localizedCallerName = "Claude"
            update.supportsHolding = false
            update.supportsGrouping = false
            update.supportsUngrouping = false
            update.supportsDTMF = false
            provider.reportNewIncomingCall(with: incomingID, update: update) { error in
                Task { @MainActor in
                    defer { completion() }
                    guard error == nil else { return }
                    guard let eventID, self.callID == nil, !self.previewing else {
                        if self.callID != incomingID {
                            self.provider.reportCall(with: incomingID, endedAt: nil, reason: .failed)
                        }
                        return
                    }
                    self.callID = incomingID
                    let connection = Store()
                    self.connection = connection
                    self.content = Task {
                        do { return try await self.load(eventID, using: connection) }
                        catch {
                            self.finish(incomingID, reason: .failed)
                            throw error
                        }
                    }
                }
            }
        }
    }

    private func load(_ id: UUID, using connection: Store) async throws -> CallContent {
        guard !connection.url.isEmpty, !connection.token.isEmpty else { throw CancellationError() }
        let event = try await connection.fetch("/events/\(id)", as: Event.self)
        guard event.id.lowercased() == id.uuidString.lowercased(),
              UUID(uuidString: event.session) != nil else { throw CancellationError() }
        let session = try await connection.fetch("/sessions/\(event.session)", as: Session.self)
        if event.kind == "attention" { return CallContent(project: session.project, batch: nil) }
        guard event.kind == "question", UUID(uuidString: event.subject) != nil else { throw CancellationError() }
        let batch = try await connection.fetch("/question-batches/\(event.subject)", as: Batch.self)
        guard batch.id == event.subject, batch.session == session.id, batch.state == "open",
              !batch.questions.isEmpty else { throw CancellationError() }
        return CallContent(project: session.project, batch: batch)
    }

    nonisolated func provider(_ provider: CXProvider, perform action: CXAnswerCallAction) {
        MainActor.assumeIsolated {
            guard action.callUUID == callID else { action.fail(); return }
            do {
                try AVAudioSession.sharedInstance().setCategory(.playAndRecord, mode: .voiceChat,
                                                                 options: [.allowBluetooth])
                answered = true
                action.fulfill()
            } catch {
                action.fail()
                finish(action.callUUID, reason: .failed)
            }
        }
    }

    nonisolated func provider(_ provider: CXProvider, didActivate audioSession: AVAudioSession) {
        MainActor.assumeIsolated {
            guard answered, let callID, let connection, let content, conversation == nil else { return }
            let voice = GermanVoice()
            self.voice = voice
            conversation = Task {
                await runConversation(callID, content: content, using: connection, voice: voice)
            }
        }
    }

    nonisolated func provider(_ provider: CXProvider, didDeactivate audioSession: AVAudioSession) {
        MainActor.assumeIsolated {
            if let callID, answered { finish(callID, reason: .failed) }
        }
    }

    nonisolated func provider(_ provider: CXProvider, perform action: CXEndCallAction) {
        MainActor.assumeIsolated {
            if action.callUUID == callID { reset() }
            action.fulfill()
        }
    }

    nonisolated func providerDidReset(_ provider: CXProvider) {
        MainActor.assumeIsolated { reset() }
    }


    private func finish(_ id: UUID, reason: CXCallEndedReason) {
        guard callID == id else { return }
        provider.reportCall(with: id, endedAt: nil, reason: reason)
        reset()
    }

    private func reset() {
        callID = nil
        answered = false
        content?.cancel()
        content = nil
        connection = nil
        conversation?.cancel()
        conversation = nil
        voice?.stop()
        voice = nil
    }

    private func runConversation(_ id: UUID, content: Task<CallContent, Error>,
                                 using connection: Store, voice: GermanVoice) async {
        do {
            let context = try await content.value
            try Task.checkCancellation()
            if let batch = context.batch {
                try await voice.say("Claude fragt im Projekt \(context.project).")
                let answers = try await voice.collect(batch.questions)
                try Task.checkCancellation()
                let submission = Submission(id: UUID(), answers: answers)
                do {
                    _ = try await connection.request("/question-batches/\(batch.id)/answers", method: "POST",
                                                     body: JSONEncoder().encode(submission))
                } catch {
                    try await voice.say("Der Versand konnte nicht bestätigt werden. Prüfe die Frage in TeleKlaus.")
                    throw error
                }
                try await voice.say("Gesendet.")
            } else {
                try await voice.say("Claude wartet im Projekt \(context.project) auf dich. Antworte in der Claude-App.")
            }
            finish(id, reason: .remoteEnded)
        } catch {
            finish(id, reason: .failed)
        }
    }

    #if DEBUG
    func preview() async throws {
        guard callID == nil, !previewing else { return }
        previewing = true
        defer { previewing = false }
        try await GermanVoice.authorize()
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord, mode: .voiceChat, options: [.defaultToSpeaker])
        try session.setActive(true)
        defer { try? session.setActive(false, options: .notifyOthersOnDeactivation) }
        let demo = GermanVoice()
        _ = try await demo.collect([Question(id: "demo", prompt: "Welche Farbe soll der Hintergrund haben?")])
        try await demo.say("Sprachtest abgeschlossen.")
    }
    #endif
}

@MainActor
private final class GermanVoice {
    private let synthesizer = AVSpeechSynthesizer()
    private struct Recognition {
        var text = ""
        var lastChange = ContinuousClock.now
        var final = false
        var error: Error?
    }

    static func authorize() async throws {
        let speech = await withCheckedContinuation { continuation in
            SFSpeechRecognizer.requestAuthorization { continuation.resume(returning: $0) }
        }
        guard speech == .authorized, await AVAudioApplication.requestRecordPermission() else {
            throw AppError("Erlaube Mikrofon und Spracherkennung in den Einstellungen.")
        }
    }

    func stop() { synthesizer.stopSpeaking(at: .immediate) }

    func say(_ text: String) async throws {
        try Task.checkCancellation()
        let utterance = AVSpeechUtterance(string: text)
        utterance.voice = AVSpeechSynthesisVoice(language: "de-DE")
        synthesizer.speak(utterance)
        defer { stop() }
        repeat {
            try await Task.sleep(for: .milliseconds(50))
        } while synthesizer.isSpeaking
    }

    func collect(_ questions: [Question]) async throws -> [AnswerRow] {
        var answers: [AnswerRow] = []
        for question in questions {
            for attempt in 0..<2 {
                try await say(question.prompt)
                let text = try await listen()
                try await say("Verstanden: \(text). Stimmt das? Sag Ja oder Nein.")
                var confirmed = Self.confirmation(try await listen())
                if confirmed == nil {
                    try await say("Sag bitte Ja oder Nein.")
                    confirmed = Self.confirmation(try await listen())
                }
                if confirmed == true {
                    answers.append(AnswerRow(question_id: question.id, text: text))
                    break
                }
                if attempt == 0 {
                    try await say("Bitte wiederhole deine Antwort.")
                } else {
                    try await say("Antwort nicht bestätigt. Die Frage bleibt in TeleKlaus offen.")
                    throw CancellationError()
                }
            }
        }
        return answers
    }

    /// true for yes, false for no, nil if unclear. Any negative word wins ("stimmt nicht").
    static func confirmation(_ spoken: String) -> Bool? {
        let words = spoken.lowercased().split(whereSeparator: { !$0.isLetter }).map(String.init)
        if words.contains(where: { ["nein", "nee", "nicht", "falsch"].contains($0) }) { return false }
        if let first = words.first,
           ["ja", "jawohl", "genau", "richtig", "stimmt", "jo", "jep", "yes"].contains(first) { return true }
        return nil
    }

    private func listen() async throws -> String {
        try Task.checkCancellation()
        guard SFSpeechRecognizer.authorizationStatus() == .authorized,
              AVAudioApplication.shared.recordPermission == .granted,
              let recognizer = SFSpeechRecognizer(locale: Locale(identifier: "de-DE")),
              recognizer.isAvailable else { throw AppError("Spracherkennung ist nicht verfügbar.") }

        let request = SFSpeechAudioBufferRecognitionRequest()
        request.requiresOnDeviceRecognition = recognizer.supportsOnDeviceRecognition
        request.shouldReportPartialResults = true
        let engine = AVAudioEngine()
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.channelCount > 0, format.sampleRate > 0 else {
            throw AppError("Kein Mikrofon verfügbar.")
        }
        var recognition = Recognition()
        let task = recognizer.recognitionTask(with: request) { result, error in
            let text = result?.bestTranscription.formattedString
            let final = result?.isFinal ?? false
            Task { @MainActor in
                if let text, text != recognition.text {
                    recognition.text = text
                    recognition.lastChange = .now
                }
                recognition.final = final
                recognition.error = error
            }
        }
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in request.append(buffer) }
        defer {
            input.removeTap(onBus: 0)
            engine.stop()
            request.endAudio()
            task.cancel()
        }
        try engine.start()

        let deadline = ContinuousClock.now.advanced(by: .seconds(30))
        while ContinuousClock.now < deadline, !recognition.final {
            if let error = recognition.error { throw error }
            if !recognition.text.isEmpty, recognition.lastChange.duration(to: .now) >= .seconds(2) { break }
            try await Task.sleep(for: .milliseconds(100))
        }
        try Task.checkCancellation()
        let text = recognition.text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { throw AppError("Keine Antwort erkannt.") }
        return text
    }
}
#endif
