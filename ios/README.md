# Claude Remote für iOS

`ClaudeRemote.xcodeproj` öffnen. Das Target erfordert iOS 17. Für die Geräteprüfung im Target das eigene Signing Team und eine eindeutige Bundle-ID setzen. Dieselbe App-ID im Apple Developer Account für Push Notifications freischalten und ein passendes Provisioning Profile wählen. Debug verwendet APNs Development, Release APNs Production. Der Dispatcher benötigt zum Profil passende Umgebung, Bundle-ID als Topic, Team-ID, Key-ID und einen privaten APNs-Schlüssel. [Apple APNs-Registrierung](https://developer.apple.com/documentation/UserNotifications/registering-your-app-with-apns)

Auf dem iPhone die HTTPS-Adresse und das Benutzer-Token eingeben, verbinden und Mitteilungen aktivieren. Einen Batch erzeugen und prüfen, ob Antippen der Mitteilung nach Authentifizierung den passenden Batch öffnet. Das Benutzer-Token liegt im gerätegebundenen Schlüsselbund. Textbetrieb ist auch über die Fragenliste verfügbar.
# TeleKlaus
