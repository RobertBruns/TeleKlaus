# TeleKlaus (Claude Remote)

**Arbeit:** `main` (`dev` ist veraltet).
**Live:** `prod` — Xcode Cloud baut die iOS-App aus `ios/ClaudeRemote.xcodeproj`. Der Dispatcher läuft auf Styx (teleklaus.rand.uber.space) und wird per Release-Verzeichnis und Symlink ausgerollt (`backend/README.md`), nie per Push. Beides nur auf Anweisung.

Bringt Entscheidungen aus laufenden Agenten-Aufgaben aufs iPhone: Dispatcher in `backend/`, Agent in `agent/`, App in `ios/`. Stand und nächste Schritte: `handoff.md`; Übergaben an andere Modelle in `handoffs/`.
