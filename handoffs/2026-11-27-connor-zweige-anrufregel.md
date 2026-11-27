# An Connor: Zweige und Anruf-Regel

Stand 27. November 2026, von Alex im Auftrag von Robert.

## Zweige

- `dev` ist auf GitHub gelöscht. Der Stand `67cbf2f` war vollständig in `main`.
- `main` ist der Arbeitszweig für alles (App, Server, Doku, Übergaben). Jederzeit pushen.
- `prod` startet Xcode Cloud. Nur auf Roberts Ansage `main` nach `prod` bringen, als Fast-Forward.
- Steht so in [PROJEKT.md](../PROJEKT.md). Offen bei Robert: `AGENTS.md` sagt allgemein „Jeder `prod` hat einen `dev`“. Bis er entscheidet, gilt für TeleKlaus `PROJEKT.md`.

## Anruf-Regel (Server, Commit auf `main`, noch nicht auf Styx)

- Es klingelt nur noch bei `question`-Ereignissen, also Fragen aus `tk-claude`.
- `attention` (wartende interaktive Session) schickt nur noch einen normalen Push, keinen VoIP-Push.
- Für die App heißt das: Der `attention`-Zweig im Anruf bleibt, wird aber vorerst nicht mehr ausgelöst. Nicht entfernen.
- Anruftest Schritt 4 aus [2026-11-27-alex-anruftest.md](2026-11-27-alex-anruftest.md) entfällt dadurch. Schritt 3 (Ablehnen) bleibt offen.

## Weiterhin offen für dich

Aus [2026-11-27-connor-anruftest-ergebnis.md](2026-11-27-connor-anruftest-ergebnis.md): Ja/Nein-Erkennung lockern, `PATCH /sessions/{id}/mode` beim Öffnen der App prüfen.
