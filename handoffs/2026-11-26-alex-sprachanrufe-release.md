# Sprachanrufe im Xcode-Cloud-Build (Release)

Stand 26. November 2026. Antwort von Connor auf den Auftrag, Sprachanrufe im Release-Build freizuschalten.

## Commits auf `prod`

- `0bf842e` Release setzt `SWIFT_ACTIVE_COMPILATION_CONDITIONS = TELEKLAUS_PERSONAL_CALLS` und `VOICE_INFOPLIST_FILE = ClaudeRemote/Info.plist`. Ohne die zweite Einstellung fehlte dem Release-Build auch der Hintergrundmodus `voip` (und `audio`) sowie die Mikrofon- und Spracherkennungstexte.
- `1d8083c` Normale und VoIP-Anmeldung schicken `"environment"` an `POST /api/v1/devices/register`: `"sandbox"` bei `APS_ENVIRONMENT = development` (Debug), `"production"` bei Release. Quelle ist der Info.plist-Eintrag `TeleKlausAPSEnvironment = $(APS_ENVIRONMENT)`.
- `89dc312` Build-Nummer (`CURRENT_PROJECT_VERSION`) 3 → 9.

Regel aus [handoff.md](../handoff.md) bleibt: nur persönliche Builds (TestFlight intern). Vor einer App-Store-Verteilung muss `TELEKLAUS_PERSONAL_CALLS` aus Release wieder heraus.

## Build-Nummer

Im Projekt 9. Xcode Cloud vergibt die Build-Nummer normalerweise selbst; der nächste Cloud-Build dürfte ebenfalls 9 tragen. Maßgeblich ist die Nummer, die die App am Ende der Hauptliste anzeigt.

## Knopf im Release-Build

Lokal geprüft (unsigniert, generisches iOS-Gerät, Xcode 15.2):

- Release-Build erfolgreich, enthält den Text **Sprachanrufe aktivieren**, `UIBackgroundModes` = `audio`, `voip`, `TeleKlausAPSEnvironment` = `production`.
- Debug-Build erfolgreich, `TeleKlausAPSEnvironment` = `development` → `sandbox`.

Der Knopf ist damit im Release-Build einkompiliert. Ob er im Xcode-Cloud-Build auf dem iPhone sichtbar ist und ob VoIP-Push in Produktion klingelt, ist ungeprüft: Bitte Robert nach der Installation des neuen Builds bestätigen lassen. Nach dem Update einmal neu verbinden bzw. Mitteilungen aktivieren, damit beide Tokens mit `environment` neu angemeldet werden.

## Hinweis

Seit 27. November 2026 enthält `main` sowohl `baf21ca` (AGENTS.md/PROJEKT.md) als auch alle App-Commits ab `b1a95b1` (Merge `ec25838`). Neue Arbeit läuft laut `PROJEKT.md` auf `main`, `prod` nur auf Anweisung.
