# Claude Remote für iOS

`ClaudeRemote.xcodeproj` öffnen. Das Target erfordert iOS 17. Für die Geräteprüfung im Target das eigene Signing Team und eine eindeutige Bundle-ID setzen. Dieselbe App-ID im Apple Developer Account für Push Notifications freischalten und ein passendes Provisioning Profile wählen. Debug verwendet APNs Development, Release APNs Production. Der Dispatcher benötigt zum Profil passende Umgebung, Bundle-ID als Topic, Team-ID, Key-ID und einen privaten APNs-Schlüssel. [Apple APNs-Registrierung](https://developer.apple.com/documentation/UserNotifications/registering-your-app-with-apns)

Auf dem iPhone die HTTPS-Adresse und das Benutzer-Token eingeben, verbinden und Mitteilungen aktivieren. Einen Batch erzeugen und prüfen, ob Antippen der Mitteilung nach Authentifizierung den passenden Batch öffnet. Das Benutzer-Token liegt im gerätegebundenen Schlüsselbund. Textbetrieb ist auch über die Fragenliste verfügbar.
# TeleKlaus

## Sprachanrufe lokal testen

Im Debug-Build nach dem Verbinden **Sprachanrufe aktivieren** und Mikrofon sowie Spracherkennung erlauben. Fragebatches werden erst nach Bestätigung aller Antworten gesendet. Bei einer wartenden interaktiven Session sagt TeleKlaus nur an, welches Projekt wartet.

Für den Simulator die App mit dem Startargument `-TeleKlausVoiceTest` starten und **Sprachtest** antippen. Der Test nutzt eine Beispielfrage und braucht keine Dispatcher-Verbindung. PushKit und das Klingeln bei gesperrtem iPhone werden am Gerät geprüft.

`ios/scripts/archive-device.sh` erzeugt ein Debug-Archiv und exportiert eine Development-IPA mit APNs Sandbox. Wenn Xcode das installierte Profil nicht auswählt, kann sein Dateipfad über `TELEKLAUS_PROFILE_PATH` angegeben werden. Das Skript prüft das Profil und signiert die App direkt. Die IPA über Apple Configurator auf das im Profil registrierte iPhone installieren.

Für einen persönlichen TestFlight-Build kann die Anruffunktion in Release mit `SWIFT_ACTIVE_COMPILATION_CONDITIONS=TELEKLAUS_PERSONAL_CALLS` und `VOICE_INFOPLIST_FILE=ClaudeRemote/Info.plist` aktiviert werden. Release verwendet APNs Production.
