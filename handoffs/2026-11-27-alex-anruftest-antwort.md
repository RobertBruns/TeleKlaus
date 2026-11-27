# Antwort an Alex: Ja/Nein-Erkennung und Moduswechsel

Stand 27. November 2026, von Connor. Bezug: [Ergebnis Anruftest](2026-11-27-connor-anruftest-ergebnis.md).

## Ja/Nein-Erkennung (`f4158eb`)

Umgesetzt wie vorgeschlagen, in `GermanVoice.confirmation(_:)`:

- Bestätigt: erstes Wort aus ja, jawohl, genau, richtig, stimmt, jo, jep, yes und kein Ablehnungswort.
- Abgelehnt: irgendwo nein, nee, nicht oder falsch. Ablehnung hat Vorrang („Ja nein“ und „Stimmt nicht“ gelten als Nein).
- Sonst einmal „Sag bitte Ja oder Nein.“ und erneut hören. Bleibt es unklar, zählt es als Nein. Danach gilt der bisherige Ablauf: einmal neu fragen, dann „Antwort nicht bestätigt“.

Mit Beispielsätzen geprüft. „Das ist richtig“ führt zur Rückfrage, weil nur das erste Wort zählt.

## `PATCH /sessions/{id}/mode` (`190c6fb`)

Nicht gewollt. Die ganze Zeile unter „Sitzungen“ war ein Knopf, der den Modus bei jedem Antippen umschaltete. Jetzt öffnet das Antippen ein Menü mit „Auf Autonom umstellen“ bzw. „Auf Interaktiv umstellen“. Erst diese Wahl sendet den PATCH. Bitte auf dem Server prüfen, welche Sessions dadurch versehentlich auf einen falschen Modus gewechselt sind, und sie zurückstellen.

## Stand

Debug- und Release-Build lokal erfolgreich (Xcode 15.2, unsigniert). Auf dem iPhone ist noch Build 9 ohne diese Änderungen. Für Schritt 3 (Schritt 4 entfällt laut [Zweige und Anruf-Regel](2026-11-27-connor-zweige-anrufregel.md)) und einen erneuten Test von Schritt 1 braucht es einen neuen Debug-Build, die Installation erfolgt wie bisher per `cfgutil install-app`.
