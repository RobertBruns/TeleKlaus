# Übergabe an Alex: Anruftest am iPhone

Stand 27. November 2026. Von Connor, Auftrag von Robert.

## Ausgangslage

- Auf Roberts iPhone (iOS 27.2.1) läuft der **Debug-Build 9** (APNs Sandbox), installiert per `cfgutil install-app`. TeleKlaus ist verbunden, **Sprachanrufe sind aktiviert**.
- Die App meldet Alert- und VoIP-Token mit `"environment": "sandbox"` an (`1d8083c`).
- Der Backend-Stand mit `environment` pro Gerät (`5f0fc5a`) läuft laut [handoff.md](../handoff.md) noch nicht auf Styx. Der laufende Dispatcher ignoriert das Feld und nimmt die Umgebung aus `REMOTE_APNS_SANDBOX`. Für diesen Test muss das Sandbox sein.
- Xcode Cloud Build 9 (Release, `production`) ist gebaut, aber noch nicht installiert. Der Release-Test folgt separat, siehe unten.

## Ablauf

Robert hat das iPhone in der Hand, du startest auf Capella. Nach jedem Schritt das Ergebnis notieren.

### 1. Frage per Anruf, App im Vordergrund

```sh
cd ~/test-repo
tk-claude --tk-name Anruftest -p "Bevor du etwas tust: Frag mich über TeleKlaus, welche Farbe der Knopf haben soll und ob du die Datei farbe.txt anlegen darfst. Fasse danach meine Antworten zusammen."
```

Erwartet: Es klingelt mit „Claude“. Nach dem Annehmen folgt „Claude fragt im Projekt Anruftest“, dann die Fragen, jeweils „Verstanden: … Stimmt das?“, am Ende „Gesendet“. `tk-claude` setzt fort, und die Zusammenfassung enthält Roberts Antworten.

### 2. iPhone gesperrt, App beendet

Robert wischt die App weg und sperrt das iPhone. Danach Schritt 1 mit `--tk-name Anruftest2` wiederholen. Erwartet: Es klingelt auf dem Sperrbildschirm, sonst wie in Schritt 1. Das ist der eigentliche VoIP-Test.

### 3. Ablehnen

Lauf mit `--tk-name Anruftest3` starten, Robert lehnt ab. Erwartet: Es wird nichts gesendet, die normale Mitteilung kommt, und die Frage steht in der App offen. Robert antwortet per Text, und `tk-claude` läuft weiter.

### 4. Wartende Session (`attention`)

Interaktive `claude`-Session auf Capella mit eingerichtetem `tk-notify`-Hook. Dort etwas auslösen, das eine Freigabe braucht. Erwartet: Es klingelt, die Ansage lautet „Claude wartet im Projekt … auf dich. Antworte in der Claude-App.“, dann endet der Anruf. Nichts wird gesendet.

## Wenn es nicht klingelt

1. Kommt die normale Mitteilung an? Wenn nicht, ist es ein allgemeines Push-Problem.
2. Log des Push-Workers auf Styx: VoIP-Zustellung an Topic `com.paulmakesstuff.teleklaus.voip`, APNs-Antwort und Umgebung.
3. Klingelt es, aber der Anruf endet sofort: Das Ereignis oder der Batch ließ sich nicht laden, oder der Batch war nicht mehr `open`. Robert prüft die Fehlermeldung in der App.

## Danach

- Ergebnis je Schritt als Antwort in `handoffs/` ablegen und in [handoff.md](../handoff.md) unter „Status“ eintragen.
- Release-Test: Backend-Stand mit `environment` auf Styx ausrollen (nur auf Anweisung von Robert). Dann Build 9 aus TestFlight installieren, neu verbinden (meldet `production`) und Schritte 1 und 2 wiederholen.
