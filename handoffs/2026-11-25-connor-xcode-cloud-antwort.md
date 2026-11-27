# TeleKlaus iOS und Xcode Cloud

Stand 25. November 2026. Antwort auf das [Xcode-Cloud-Handoff](2026-11-25-connor-xcode-cloud.md).

## Auf `origin/main`

- `b1a95b1` enthält PushKit, CallKit, die deutsche Sprachinteraktion und das Skript für den Entwicklungsexport mit Apple Configurator.
- `f0c85ee` ergänzt die sichtbare Buildnummer am Ende der Hauptliste und das geteilte Schema [ClaudeRemote](../ios/ClaudeRemote.xcodeproj/xcshareddata/xcschemes/ClaudeRemote.xcscheme). Das Schema nutzt Debug zum Starten und Release zum Archivieren. Das Configurator-Skript wählt Debug ausdrücklich.
- Beide Commits verwenden den lokal konfigurierten Git-Autor Robert Bruns. Die automatische Freigabe hat die Änderung des Autors auf Connor ohne direkte Autorisierung abgelehnt.

## Workflow „Push“

Für den Workflow sind das Repository `RobertBruns/TeleKlaus`, das Projekt `ios/ClaudeRemote.xcodeproj` und das Schema `ClaudeRemote` vorgesehen. Der Projektpfad und das Schema wurden im Git-Stand und durch lokale Xcode-Builds geprüft. Die in Xcode Cloud gespeicherten Einstellungen ließen sich in dieser Sitzung nicht auslesen. Ob Xcode Cloud das Projekt neu auswählen muss und ob der Workflow bereits darauf zeigt, bleibt offen.

Die zur Prüfung genannte Cloud-Ausführung war Build 4 auf `prod` (`58b1654`). Ein aktuelles Cloud-Ergebnis wurde nicht verifiziert. Der Weg von `main` nach `prod` ist mit Robert abzustimmen.

## Lokale Build-Ergebnisse

- Debug-Build mit dem geteilten Schema für ein generisches iOS-Gerät erfolgreich.
- Release-Archiv über die Archive-Aktion des geteilten Schemas erfolgreich. Beide Prüfungen liefen ohne Codesignierung.
- Für einen persönlichen Release-Build mit dem Knopf **Sprachanrufe aktivieren** sind die beiden Build-Einstellungen in der [iOS-README](../ios/README.md) erforderlich. Der lokale Debug-Build enthält die Funktion standardmäßig.
