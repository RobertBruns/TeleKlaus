# An Connor: Sprachanrufe fehlen in der installierten App

Stand 24. November 2026, von Alex im Auftrag von Robert. Bezug: [Auftrag CallKit](2026-11-24-connor-callkit.md).

## Beobachtung

- Robert findet in der installierten App ClaudeRemote keinen Knopf „Sprachanrufe aktivieren“.
- Die App ist mit dem Dispatcher verbunden. Seit 21:49 lädt sie Sessions, Fragen und Ereignisse und ruft bei jedem Aktualisieren `POST /api/v1/devices/register` auf.
- Auf dem Server bleibt es bei genau einem Gerät mit `kind = alert`. Es kommt kein VoIP-Token an.
- Auf GitHub (`main`) liegt kein App-Stand von dir. Neuester Commit ist `67cbf2f` (Übergabe).

## Vermutung

Entweder läuft auf dem iPhone noch der alte Build, oder der neue Build enthält den Knopf nicht bzw. an anderer Stelle.

## Bitte

1. Deinen App-Stand als `Connor <connor@noreply.local>` auf `main` committen und pushen, nicht auf `prod`.
2. Sagen, wo „Sprachanrufe aktivieren“ in der Oberfläche steht.
3. Build-Nummer erhöhen und in der App sichtbar machen, damit erkennbar ist, welcher Build läuft. Im Zweifel die alte App vorher löschen und neu installieren.
4. Ergebnis hier im Ordner `handoffs/` als neue Datei oder direkt an Robert melden.
