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
        var status = SecItemUpdate(query as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var entry = query
            entry[kSecValueData as String] = data
            entry[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
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
                                  body: JSONEncoder().encode(["token": value]))
        } catch { problem = error.localizedDescription }
    }
}

private final class Notifications: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    static let store = Store()

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
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
            }
            .navigationTitle("Claude Remote")
            .refreshable {
                if store.connected {
                    do { try await store.reload() } catch { store.problem = error.localizedDescription }
                }
            }
            .sheet(item: $store.selected) { AnswerSheet(store: store, batch: $0) }
            .alert("Claude Remote", isPresented: Binding(
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
