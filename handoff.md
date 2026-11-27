# Claude Remote — Handoff
Stand: 2026-11-24

## Status
Beide Uberspace-Accounts wurden lesend inventarisiert. Der M0-Resume-Test im freigegebenen Test-Repo hat die Frage-Antwort-Fortsetzung über einen flüchtigen Dispatcher bestätigt.

Ein M1-Textprototyp mit FastAPI/SQLite, verwaltetem Agent-Job, SwiftUI und normalem APNs-Versandcode ist im Workspace vorhanden. Der unsignierte iPhone-Build ist erfolgreich. Der kombinierte Routing-Test mit zwei echten Claude-Sessions und die Wiederanlauf- und Deduplizierungstests wurden bestanden.

Am 24. November 2026 lief der Dispatcher als User-Service auf Styx unter `https://teleklaus.rand.uber.space` und der Agent auf Capella. Eine auf dem iPhone beantwortete Frage wurde derselben Claude-Session zugestellt und bestätigt. Der Dienst lief nach Logout weiter. Linger ist für `rand` aktiv, ein Hostneustart ist ungeprüft. Der Push-Worker läuft als User-Service auf Styx. Eine Push-Mitteilung (APNs Sandbox) kam auf dem iPhone an und öffnete den Fragebatch. Der Agent läuft noch nicht als Dienst. Mit `agent/tk_claude.py` fragt eine per Skript gestartete Claude-Session von sich aus über das Telefon nach und setzt nach der Antwort fort; am 24. November 2026 in `test-repo` mit drei Fragen belegt. Interaktive Sessions auf Capella melden Wartezustände über den Hook `agent/tk_notify.py` als `attention`-Ereignis mit Push; am 24. November 2026 auf dem iPhone belegt.

Offen sind der Zwei-Job-Versuch über HTTPS, Sandbox und Produktion gleichzeitig im Push-Worker, die automatische Auflösung eines Absturzes mitten im Resume. Speech und VoIP sind ungeprüft.

[Machbarkeit](docs/feasibility.md) · [Testnachweise](docs/test-plan.md)

## Ziel
Native SwiftUI-App und selbst gehosteter FastAPI-Dispatcher
für mehrere Claude-Code-Sessions.

Zuerst M1: zuverlässiger Textbetrieb.
Voice und CallKit erst nach erfolgreicher Machbarkeitsprüfung.

## Benötigte Umgebung
- Bestehender Entwicklungs-Uberspace mit Claude Code.
- Separater Uberspace für Dispatcher.
- SSH-Zugang unter Kontrolle des Nutzers.
- Python/venv, persistenter Speicher, Prozessüberwachung.
- HTTPS-Hostname mit gültigem TLS.
- Später: Mac/Xcode, physisches iPhone, Apple Developer
  Program, Bundle-ID, Provisioning und APNs-Schlüssel.
- Kein Docker oder Root vorgesehen.

## Nächste Schritte
1. `tk-claude` in ein echtes Skript übernehmen (imagePipeline braucht vorher eine Sperre gegen parallele Läufe).
2. Anruf als weiterer Benachrichtigungsweg: Telefonie-Anbieter oder CallKit entscheiden.
3. Agent als Dienst auf Capella betreiben und den Zwei-Job-Versuch über HTTPS wiederholen.
4. Push-Worker: erledigt im Backend (25. November 2026, noch nicht auf Styx): Grund aus der APNs-Antwort wird protokolliert, tote Tokens (`BadDeviceToken`, `Unregistered`, `DeviceTokenNotForTopic`, 410) löschen das Gerät, andere dauerhafte 4xx nur die Zustellung, abgelaufenes Provider-Token wird erneuert und wiederholt. Geräte speichern ihre APNs-Umgebung (Migration 004, optionales Feld `environment`: `sandbox`/`production` bei `POST /devices/register`; fehlt es, gilt `REMOTE_APNS_SANDBOX`). Die App schickt `environment` mit (Debug-Build `sandbox`, TestFlight/App Store `production`; `1d8083c`, Build 9). Offen: VoIP-Zustellungen, die nach einer Wiederholung älter als ihr Ablauf (120 s) sind, werden noch versucht.
5. Wiederaufnahme von `tk-claude` nach Absturz während des Wartens.

## M1
- FastAPI, SQLite, Migrationen.
- Agent mit ausgehender authentifizierter Verbindung.
- Dauerhafte Session-Bindung und Entscheidungszustände.
- SwiftUI: Anmeldung, Sessions, Fragen, Textantworten,
  Freigabe/Ablehnung und Verlauf.
- Normale APNs mit ausschließlich opaken IDs.
- Wiederanlauf, Deduplizierung und Isolation testen.
- Installations-, Update- und Rollback-Anleitung liefern.

## Unverhandelbare Regeln
- Keine Anrufe aus interaktiven Sessions.
- Keine blinde tmux-Tastatureingabe.
- Stop-Hook bedeutet nicht Aufgabenabschluss.
- Antworten niemals als Shell-Befehle ausführen.
- Entscheidungen strikt an Tenant/Host/Session/Batch binden.
- Keine Fortsetzung behaupten, bevor sie bestätigt wurde.
- Kein PushKit für simulierte lokale TTS-Anrufe. Ausnahme seit 24. November 2026 (Entscheidung Robert): Anruf-Variante B mit Sprachausgabe und -erkennung auf dem iPhone, ausschließlich für persönliche Debug- und TestFlight-Builds. Vor einer App-Store-Verteilung auf Variante A (Sprache auf dem Server, echter Medienpfad) umstellen.
- Speech und echte VoIP-Medien separat validieren.
- Keine ungeprüfte CarPlay-Kompatibilität behaupten.
- Keine Secrets in Quellcode, Push-Nachrichten oder Chat.

Das ursprüngliche MVP-Briefing bleibt maßgeblich.