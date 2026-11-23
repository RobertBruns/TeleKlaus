# Claude Remote – Architekturentscheidung und Machbarkeit

## Verifizierter Stand

Am 21. November 2026 enthielt der Workspace bei der Übernahme nur `handoff.md` und war kein Git-Repository. In den geprüften übergeordneten Verzeichnissen und im Workspace lag keine `AGENTS.md`. Das vollständige beigefügte MVP-Briefing ist lesbar und maßgeblich. Auf dem Mac melden die Programme Claude Code 2.1.150 und Xcode 15.2. Das Inventarskript wurde neu erstellt. Die Ergebnisse des Entwicklungsaccounts stehen unten. Die Ergebnisse des Dispatchers stehen ebenfalls unten. Der M0-Resume-Nachweis ist dokumentiert. Das iPhone ist ungeprüft.

## Entwicklungs-Uberspace

Die lesende SSH-Inventur am 21. November 2026 war über `paule@capella.uberspace.de` erfolgreich. Der Kurzname `capella` ließ sich lokal nicht auflösen. Auf dem Shared Host läuft Linux 3.10. Der Account hat laut cgroup v1 ein RAM-Limit von 1,5 GiB und ein kombiniertes RAM-/Swap-Limit von 1,5 GiB. Die CPU-Quote beträgt 300.000 µs pro 100.000 µs, also bis zu drei CPU-Kerne. Die Shell meldet maximal 1.024 Prozesse und 1.024 offene Dateien als Softlimit, 4.096 als Hardlimit. `df` meldete rund 320 GiB frei auf dem Shared-Dateisystem. Die Account-Quota-Abfrage erreichte ihr Zeitlimit. Das tatsächliche Speicherkontingent bleibt offen.

`python3` liefert 3.6.8 mit SQLite 3.54.1. Explizit verfügbar sind Python 3.10.22, 3.11.18, 3.12.16 und 3.13.18 sowie Node 20.20.2. Eine isolierte venv mit M1-Abhängigkeiten wurde noch nicht getestet.

Supervisor antwortet und verwaltet bestehende Dienste. Zwei liefen und einer meldete einen fehlenden Programmstartpfad. Die Webkonfiguration zeigt Apache als Standard und mindestens einen aktiven Proxy auf einen lokalen Dienst. Ausgehendes HTTPS zu Anthropic funktionierte bis zur HTTP/2-Antwort 404 auf die Wurzel-URL. Eingehendes TLS am künftigen Dispatcher, WebSocket-Upgrade und HTTPS zwischen den Accounts bleiben offen.

Claude Code 2.1.296 liegt unter `~/.local/bin/claude`. Zwei aktive Claude-Prozesse hatten Bash als Elternprozess und ein Pseudoterminal. Das belegt Terminalstarts. Der genaue Startbefehl und eine mögliche übergeordnete Multiplexer-Nutzung sind noch offen. Die laufenden Claude-Prozesse wurden nur inventarisiert.

## Dispatcher-Uberspace

Die lesende SSH-Inventur am 21. November 2026 war über `rand@styx.uberspace.de` erfolgreich. Python 3.14.10 lädt `venv` und SQLite 3.54.1. Das Installieren der M1-Abhängigkeiten ist noch zu prüfen.

In cgroup v2 setzt der User-Slice `memory.max` auf 1.572.864.000 Bytes (1.500 MiB), `cpu.max` auf `300000 100000` (drei Kerne) und `pids.max` auf 2.254 Tasks. Beim Messzeitpunkt belegte der Slice rund 42 MiB. `df` meldete rund 339 GiB frei auf dem Shared-Dateisystem. `quota -s` lieferte vor dem harten Zeitlimit kein Ergebnis. Ein Uberspace-CLI-Unterbefehl `quota` war nicht vorhanden. Account-Speicherkontingent und Persistenz über Neustarts bleiben offen.

`supervisorctl` war nicht im PATH. Der systemd-Benutzermanager antwortete mit Version 262.2 und `SystemState=running`. Die Linger-Abfrage wurde verweigert. Der Benutzerbetrieb über Logout und Neustart bleibt zu prüfen, bevor daraus ein Installationsablauf abgeleitet wird.

Als Webroute war nur der Apache-Standard konfiguriert. `https://rand.uber.space/` lieferte bei der TLS-Prüfung vom Dispatcher aus HTTP 200 über HTTP/2. Der ausgehende Test zur APNs-Sandbox lieferte HTTP 405 über HTTP/2 und belegt die Erreichbarkeit. APNs-Authentifizierung, Zustellung, HTTPS zwischen den Accounts, App-Proxy und WebSocket-Upgrade sind separat offen.

## Architekturentscheidung

Für M1 ist ein eigener Dispatcher mit FastAPI, SQLite und Migrationen vorgesehen. Der Agent fragt Entscheidungen über ausgehendes authentifiziertes HTTPS ab. Das iPhone authentifiziert sich getrennt und lädt Details anhand opaker Ereignis-IDs. Persistente Zuordnungen verknüpfen Tenant, Host, Session, Batch und Entscheidung. Der Agent quittiert erst nach nachgewiesener Fortsetzung in der gebundenen Claude-Session. Eine nach einem Absturz unklare Ausführung muss vor einem erneuten Resume abgeglichen werden.

Die bevorzugte Resume-Hypothese ist ein von uns gestarteter Claude-Prozess mit dokumentierter Resume-Schnittstelle, fester Session-ID und exklusiver Zuständigkeit des Agents. Die CLI dokumentiert Resume nach ID. Der Agent SDK dokumentiert auch die Wiederaufnahme nach einem Prozessneustart. Ob sich die Methode mit der installierten Version, deren Konfiguration und dem gewünschten Ablauf zuverlässig betreiben lässt, entscheidet der Versuch im freigegebenen Testprojekt. Ein Stop-Hook wird als Ende eines Turns behandelt. [CLI-Referenz](https://code.claude.com/docs/en/cli-reference) · [Agent SDK Sessions](https://code.claude.com/docs/en/agent-sdk/sessions)

## Ergebnis des Resume-Gates

Im freigegebenen Projekt `/home/paule/repositories/test-repo` auf Capella hat Claude Code 2.1.296 zwei isolierte CLI-Versuche bestätigt. Ein dritter Versuch mit Session `65f4cea1-cd0f-4192-ba0d-851b5cf3ae44` transportierte den Batch über den lokalen Testtreiber zu einem flüchtigen SQLite-Dispatcher auf Styx. Der Dispatcher legte Entscheidung `4521ea4132c1` für diese Session an. Ein neuer Claude-Prozess nahm dieselbe Session-ID wieder auf und bestätigte den Entscheidungswert zusammen mit einer Kennung aus dem ersten Turn. Erst danach quittierte der Dispatcher die Zustellung. Die Kennung wurde beim Resume nicht erneut mitgegeben. Der Test ist mit `scripts/resume-probe.py` reproduzierbar.

Der Versuch belegt verwaltete CLI-Turns mit deaktivierten Werkzeugen sowie projektgebundenes Resume nach Prozessende. Er nutzt SSH als Testtransport und eine simulierte Bedienentscheidung. Für M1 sind dauerhafte Zustellung über HTTPS, Agent-Wiederanlauf und die Gerätekette gesondert zu prüfen.

## Machbarkeitsmatrix

| Gate | Offener Nachweis | Freigabekriterium |
| --- | --- | --- |
| Beide Hosts | Python und Supervisor, Kontingente, CPU, RAM, Prozesslimits, Speicher, Listener, HTTPS und Proxy | Werte mit Quelle und Geltungsbereich je Account. Shared-Host-Werte gelten nur als Kontext. Fehlende Limits bleiben offen. |
| Session-Resume | Verwaltetes CLI-Resume bestanden. Hooks und laufende interaktive Sitzungen bleiben offen. | Dieselbe Session-ID liefert Frage und bestätigte Fortsetzung. Das Ergebnis enthält Kontext des ersten Turns, der im Antwortturn nicht erneut übergeben wurde. |
| Text und normale APNs | Entwicklungs-APNs vom Dispatcher, signiertes Gerät, authentifiziertes Nachladen | Push mit opaker ID öffnet den passenden Batch. Versand- und Gerätezustellung sind separat belegt. [Apple APNs-Registrierung](https://developer.apple.com/documentation/UserNotifications/registering-your-app-with-apns) |
| Speech | Kokoro und lokales STT auf dem Dispatcher, iOS-Vergleich | Peak-RSS, CPU, Kaltstart, Zeit bis zur ersten Audioausgabe, Echtzeitfaktor, deutsche Sprachqualität und Auswirkung paralleler Prozesse messen. Medien/Compute bei Bedarf auslagern oder einen dokumentierten Fallback wählen. |
| VoIP und CarPlay | Medienpfad, Signierung, Hintergrundbetrieb und physisches iPhone | Echten bidirektionalen Anruf nachweisen. CarPlay separat testen. |

## Reihenfolge und Stop/Go

1. Nach Erhalt der SSH-Ziele beide Inventuren mit `ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes <ziel> bash -s -- dev < scripts/inventory.sh` ausführen. Für den zweiten Account `dispatcher` als Rolle verwenden. Die Inventur liest Supervisor- und Webkonfiguration. WebSocket-Upgrade und Persistenz über Neustarts separat prüfen, sobald eine freigegebene Testadresse beziehungsweise ein Testdienst existiert. [Uberspace Web Backends](https://manual.uberspace.de/web-backends/)
2. Auf dem Entwicklungsaccount die Prozesshierarchie mit dem tatsächlich verwendeten Startweg abgleichen. Im freigegebenen Projekt eine Session mit einer Testkennung starten und einen strukturierten Fragebatch erfassen. Die Antwort über eine kleine Testübergabe mit Entscheidungs-ID weiterreichen. Einen neuen Prozess im selben Projekt mit der exakt gebundenen Session-ID fortsetzen. Erwartetes Ergebnis sind die aus dem ersten Turn erinnerte Kennung, die verarbeitete Entscheidung und ein überprüfbarer Testfortschritt. Anschließend mit neuer Session wiederholen. Kein M1-Start vor bestandenem Resume-Gate.
3. M1 bauen und mit zwei parallelen Sessions prüfen. Entscheidungen getrennt zustellen. Wiederholte Events und Acks sowie Neustarts vor und nach der Fortsetzung testen. iPhone und APNs auf einem signierten Gerät prüfen.
4. Sprach- und VoIP-Gates separat nach dem zuverlässigen Textablauf angehen.
