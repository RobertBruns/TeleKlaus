# An Connor: Ergebnis Anruftest am iPhone

Stand 27. November 2026, von Alex. Bezug: [Anruftest](2026-11-27-alex-anruftest.md). Debug-Build 9, APNs Sandbox, Server-Release `86045e9`.

| Schritt | Ergebnis |
| --- | --- |
| 1. App offen | Klingelt. App lädt Ereignis, Session und Batch 2 s nach dem Push. Ansage und Fragen hörbar, Erkennung liefert Text, Rückfrage „Stimmt das?“ kommt. Bestätigung scheiterte zweimal, Anruf endete mit „Antwort nicht bestätigt“, nichts gesendet. Text-Antwort in der App danach: `tk-claude` setzt fort, Aufgabe erledigt. |
| 2. Gesperrt, App weggewischt | Klingelt auf dem Sperrbildschirm, App wird geweckt, Sprachantwort „Ein Zebra“ bestätigt und gesendet. `tk-claude` setzt fort, `tier.txt` angelegt. **Bestanden.** |
| 3. Ablehnen | Noch offen. |
| 4. `attention` | Noch offen. |

## Bitte: Ja/Nein-Erkennung lockern

In `collect` gilt nur exakt `["ja"]` als Bestätigung. „Ja, stimmt“, „Jawohl“, „Genau“, „Jo“ scheitern. Vorschlag:

- Bestätigt: erstes Wort aus ja, jawohl, genau, richtig, stimmt, jo, jep, yes, und kein Wort aus nein, nee, nicht, falsch.
- Abgelehnt: eines aus nein, nee, nicht, falsch.
- Sonst einmal „Sag bitte Ja oder Nein“ und erneut hören.

## Nebenbei

Beim Öffnen setzt die App `PATCH /sessions/{id}/mode` für eine interaktive Claude-Session (zweimal beobachtet). Bitte prüfen, ob das gewollt ist. Ein Wechsel auf `interactive` würde neue Fragen dieser Session ablehnen.
