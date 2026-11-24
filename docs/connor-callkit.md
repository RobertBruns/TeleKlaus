# Übergabe an Connor: Anruf per CallKit (Variante B)

Stand 24. November 2026. Auftrag von Robert über Alex. Commits als `Connor <connor@noreply.local>`.

## Ziel

Eine offene Frage oder eine wartende Claude-Session lässt das iPhone klingeln. Nach dem Annehmen liest die App die Frage auf Deutsch vor, nimmt die gesprochene Antwort auf, liest sie zur Bestätigung vor und sendet sie. Sprachausgabe und -erkennung laufen auf dem iPhone (Variante B). Das ist nur für persönliche Debug- und TestFlight-Builds freigegeben, siehe Regeln in [handoff.md](../handoff.md).

## Server (fertig, läuft auf Styx)

| Was | Wert |
| --- | --- |
| VoIP-Token registrieren | `POST /api/v1/devices/register` mit `{"token": "<hex>", "kind": "voip"}` und Benutzer-Token. Der bisherige Alert-Token bleibt mit `kind` weggelassen oder `"alert"`. |
| VoIP-Push | Topic `com.paulmakesstuff.teleklaus.voip`, Sandbox für Debug-Export. Payload nur `{"event_id": "<uuid>"}`. Ablauf nach 2 Minuten. |
| Wann es klingelt | Ereignisse `question` (Fragebatch) und `attention` (Session wartet). |
| Ereignis laden | `GET /api/v1/events/{event_id}` → `{seq, id, session, kind, subject, detail}`. |
| Frage laden | Bei `question` ist `subject` die Batch-ID: `GET /api/v1/question-batches/{subject}` → `{id, session, state, summary, questions: [{id, prompt}]}`. Nur `state == "open"` vorlesen. |
| Antwort senden | `POST /api/v1/question-batches/{id}/answers` mit `{"id": "<neue uuid>", "answers": [{"question_id", "action": "answer", "text"}]}`. Jede Frage genau einmal. |
| `attention` | `detail` enthält z. B. `TeleKlaus: Claude needs your permission to use AskUserQuestion`. Nur ansagen, nichts senden. Geantwortet wird in der Claude-App. |

## App

1. Capabilities: Background Modes „Voice over IP“ und „Audio“. Info.plist: `NSMicrophoneUsageDescription`, `NSSpeechRecognitionUsageDescription`.
2. PushKit: `PKPushRegistry` mit `.voIP`. Den Token als Hex an `devices/register` mit `kind: "voip"` senden, sobald Adresse und Benutzer-Token vorliegen. Bei Token-Wechsel erneut.
3. Eingehender VoIP-Push: **sofort und synchron** `CXProvider.reportNewIncomingCall` mit Anrufer „Claude“ melden, noch vor jedem Netzwerkaufruf. iOS beendet die App sonst und stellt keine VoIP-Pushes mehr zu. Danach Ereignis und Batch laden. Schlägt das fehl oder ist der Batch nicht mehr offen, den Anruf mit `.failed` beenden.
4. Annehmen: Audio erst in `provider(_:didActivate:)` nutzen (`.playAndRecord`, Modus `.voiceChat`), nicht selbst aktivieren.
   - `question`: „Claude fragt im Projekt X.“ Dann je Frage: vorlesen (`AVSpeechSynthesizer`, `de-DE`), Antwort aufnehmen (`SFSpeechRecognizer` `de-DE`, wenn möglich on-device; Ende nach etwa 2 s Stille, höchstens 30 s), vorlesen „Verstanden: … Stimmt das?“, Ja oder Nein erkennen. Bei Nein einmal neu fragen. Danach alle Antworten senden, „Gesendet“ sagen, Anruf beenden.
   - `attention`: „Claude wartet im Projekt X auf dich. Antworte in der Claude-App.“ Anruf beenden.
5. Ablehnen oder verpasst: nichts senden. Die Frage bleibt in der App offen, der normale Push kommt weiterhin.
6. Gesprochene Antworten sind reiner Text. Nichts davon ausführen. Keine Inhalte in Logs.

## Test

1. Debug-Build wie bisher exportieren und installieren, Mitteilungen und Mikrofon erlauben, App einmal öffnen, damit der VoIP-Token registriert wird.
2. Alex prüft auf Styx, dass ein Gerät mit `kind = voip` existiert, und startet über `tk-claude` eine Frage.
3. iPhone klingelt, Robert nimmt an, beantwortet per Sprache. Alex prüft die Antwort in der Claude-Session.
4. Zusätzlich eine Frage in einer Claude-Session auf Capella auslösen (`attention`).

Melden: Build-Ergebnis, Abweichungen von dieser Beschreibung, offene Fragen.
