# Claude Remote — Handoff
Stand: 2026-11-24

## Status
Beide Uberspace-Accounts wurden lesend inventarisiert. Der M0-Resume-Test im freigegebenen Test-Repo hat die Frage-Antwort-Fortsetzung über einen flüchtigen Dispatcher bestätigt.

Ein M1-Textprototyp mit FastAPI/SQLite, verwaltetem Agent-Job, SwiftUI und normalem APNs-Versandcode ist im Workspace vorhanden. Der unsignierte iPhone-Build ist erfolgreich. Der kombinierte Routing-Test mit zwei echten Claude-Sessions und die Wiederanlauf- und Deduplizierungstests wurden bestanden.

Am 24. November 2026 lief der Dispatcher als User-Service auf Styx unter `https://teleklaus.rand.uber.space` und der Agent auf Capella. Eine auf dem iPhone beantwortete Frage wurde derselben Claude-Session zugestellt und bestätigt. Der Dienst lief nach Logout weiter. Linger ist für `rand` aktiv, ein Hostneustart ist ungeprüft. Der Push-Worker läuft als User-Service auf Styx. Eine Push-Mitteilung (APNs Sandbox) kam auf dem iPhone an und öffnete den Fragebatch. Der Agent läuft noch nicht als Dienst.

Offen sind der Zwei-Job-Versuch über HTTPS, Sandbox und Produktion gleichzeitig im Push-Worker, modellinitiierte Fragen über installierte Skills/Hooks und die automatische Auflösung eines Absturzes mitten im Resume. Speech und VoIP sind ungeprüft.

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
1. Agent als Dienst auf Capella betreiben und den Zwei-Job-Versuch über HTTPS wiederholen.
2. Push-Worker: APNs-Fehlergrund protokollieren, dauerhaft abgelehnte Zustellungen verwerfen, APNs-Umgebung je Gerät speichern.
3. Modellinitiierte Fragen und Wiederanlauf innerhalb eines Claude-Turns ergänzen.

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
- Kein PushKit für simulierte lokale TTS-Anrufe.
- Speech und echte VoIP-Medien separat validieren.
- Keine ungeprüfte CarPlay-Kompatibilität behaupten.
- Keine Secrets in Quellcode, Push-Nachrichten oder Chat.

Das ursprüngliche MVP-Briefing bleibt maßgeblich.