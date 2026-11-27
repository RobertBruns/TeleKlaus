# Übergabe an Alex und Robert: TeleKlaus Debug-Build 11

Stand 27. November 2026, Cody. Fortsetzung der [Übergabe zur Ja/Nein-Erkennung](2026-11-27-alex-anruftest-antwort.md).

## Stand auf dem Mac und iPhone

- Build 11 wurde mit Xcode als Debug-Archiv gebaut, mit dem vorhandenen Entwicklungsprofil signiert und als `builds/TeleKlaus-Debug-11.ipa` abgelegt. Die Signaturprüfung war erfolgreich. Apple Configurator hat die Installation auf Roberts iPhone bestätigt. Debug verwendet APNs Sandbox.
- Build 11 enthält die gelockerte Ja/Nein-Erkennung und den expliziten Moduswechsel per Menü. Für Anrufe bevorzugt er installierte deutsche Stimmen in der Reihenfolge Premium, Erweitert, Standard. Die Anrufeinstellungen zeigen die verwendete Stimme an. Die Siri-Stimme steht Apps über diese Sprachausgabe-API nicht zur Verfügung. [Apple Developer](https://developer.apple.com/videos/play/wwdc2020/10022/?time=394)
- `main` auf GitHub enthält seit Merge `cd61b56` sowohl Connors App-Commits `0f4c9c3` und `83c4734` als auch Alex' neuere Backend- und Agenten-Commits. `prod` wurde nicht aktualisiert. Xcode Cloud und der Dispatcher auf Styx waren nicht Teil dieses Laufs.

## Offen

1. Mit Robert am iPhone [Anruftest Schritt 1](2026-11-27-alex-anruftest.md) wiederholen. Die angezeigte deutsche Stimme prüfen und eine natürliche Bestätigung wie „Ja, genau“ testen. Falls nur die Standardstimme angezeigt wird, kann Robert eine deutsche Premium-Stimme in den Bedienungshilfen herunterladen.
2. Schritt 3 durchführen. Robert lehnt den Anruf ab. Die Frage soll offen bleiben, die normale Mitteilung soll ankommen, und die Textantwort soll `tk-claude` fortsetzen. Schritt 4 entfällt laut [Anruf-Regel](2026-11-27-connor-zweige-anrufregel.md).
3. Auf Styx prüfen, ob vor dem App-Fix Sitzungsmodi versehentlich geändert wurden. Den ursprünglichen Modus anhand der verfügbaren Belege ermitteln, bevor eine Korrektur erfolgt.
4. Die Ergebnisse in dieser Übergabe und im [Projektstatus](../handoff.md) festhalten. Die Installation bestätigt noch keinen Anruf oder Push-Empfang mit Build 11.
