# An Connor: Xcode Cloud schlägt fehl, App-Stand fehlt auf GitHub

Stand 25. November 2026, von Alex im Auftrag von Robert. Vorher: [Rückfrage Knopf](2026-11-24-connor-callkit-fehlt.md).

## Beobachtung

- Xcode Cloud, Workflow „Push“, Build 4 auf `prod` (Commit `58b1654`): „Project ClaudeRemote.xcodeproj does not exist at ios/ClaudeRemote.xcodeproj“.
- Im Repo liegt das Projekt auf `prod` und `main` genau dort: `ios/ClaudeRemote.xcodeproj/project.pbxproj`.
- Es gibt kein geteiltes Schema (`ios/ClaudeRemote.xcodeproj/xcshareddata/xcschemes/`). Xcode Cloud braucht eines.
- Auf keinem Zweig liegt ein App-Stand mit PushKit oder CallKit. `prod` ist die alte App.

## Bitte, in dieser Reihenfolge

1. Deinen App-Stand (PushKit, CallKit, Sprache, sichtbare Build-Nummer) als `Connor <connor@noreply.local>` auf `main` committen und pushen.
2. Schema „ClaudeRemote“ als Shared markieren und die Datei unter `xcshareddata/xcschemes/` mit committen.
3. Workflow „Push“ in Xcode bearbeiten: Repository muss `RobertBruns/TeleKlaus` sein, Projekt `ios/ClaudeRemote.xcodeproj`. Projekt neu auswählen, falls der Workflow aus der Zeit vor dem Umzug nach `ios/` stammt (Commit `1f7d983`).
4. Erst danach `main` nach `prod` bringen. Den Weg nach `prod` mit Robert abstimmen.
5. Ergebnis als neue Datei in `handoffs/` melden: Commit, Schema, Workflow-Einstellungen, Build-Ergebnis.
