# Claude Remote ausprobieren und betreiben

Die Abschnitte bauen aufeinander auf. Der lokale Test braucht nur den Mac. Der kombinierte Versuch braucht zusätzlich SSH zu Capella und das freigegebene Testprojekt. Für den Einsatz mit dem iPhone kommen ein HTTPS-Dispatcher und Apple-Signing hinzu.

## 1. Auf dem Mac prüfen

Im Projektordner mit Python 3.14 eine Umgebung anlegen und die Tests ausführen.

```sh
python3.14 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
.venv/bin/python -B -m unittest discover -s backend -v
.venv/bin/python -B -m unittest discover -s agent -v
```

Der Backend-Test registriert zwei Sitzungen, weist eine Frage im interaktiven Modus ab und prüft, dass ein doppelter Batch nur ein Ereignis erzeugt. Danach startet die API mit derselben SQLite-Datei erneut. Die Entscheidung ist weiter da, ein Ack aus der falschen Sitzung liefert HTTP 404 und ein zweiter richtiger Ack erzeugt kein weiteres Ereignis. Die Agent-Tests decken verlorene Acks und den Halt bei unklarem Resume ab.

## 2. Zwei echte Claude-Sitzungen sehen

Vom Mac aus mit eingerichtetem SSH-Zugang ausführen.

```sh
.venv/bin/python -B scripts/demo-two-sessions.py \
  --dev paule@capella.uberspace.de \
  --project repositories/test-repo
```

Die Demo startet zwei neue Claude-Sitzungen im freigegebenen Projekt, beantwortet nur Batch A und prüft nach dem API-Neustart, dass A bestätigt und B offen ist. Am Ende erscheinen die beiden Sitzungs-IDs und die ID der bestätigten Entscheidung. Der Dispatcher läuft dabei auf dem Mac im Testclient und der Claude-Aufruf erfolgt auf Capella per SSH. Für den separaten M0-Versuch mit flüchtigem SQLite-Relay auf Styx dient `scripts/resume-probe.py --help`. [Testplan](test-plan.md)

## 3. Den Dispatcher für HTTPS vorbereiten

| Entscheidung | Wo sie gebraucht wird |
| --- | --- |
| Release, privater Datenordner und freier Port | Auf `rand@styx.uberspace.de` |
| HTTPS-Route für Claude Remote | Im Uberspace-Webfrontend auf Styx |
| Datenbankpfad, Agent-Token und Benutzer-Token | In der privaten Dispatcher-Umgebung |
| Agent-Token und Basis-URL | In der privaten Agent-Umgebung auf Capella |
| Benutzer-Token und dieselbe Basis-URL | In der App auf dem iPhone |

Die [Backend-Anleitung](../backend/README.md) beschreibt das Anlegen der venv, die systemd-Unit, Update und Rollback. Die produktive Datenbank gehört in einen privaten Ordner außerhalb des Releases. Die Route soll auf den gewählten Anwendungsport zeigen. Der nächste Schritt setzt einen erfolgreichen Aufruf der öffentlichen Test-URL voraus.

```sh
curl --fail --show-error 'https://DEINE-BASIS-URL/api/v1/health'
```

Erwartet wird `{"ok":true}`. Prüfe getrennt, ob die Unit nach SSH-Logout und späterem Neustart des Hosts wieder läuft. Linger ist aktiv, wenn `rand` in `/var/lib/systemd/linger` steht. `loginctl` verweigert die Abfrage. Am 24. November 2026 war das der Fall und der Dienst lief nach Logout weiter.

## 4. Auf Capella einen Textjob starten

Die Datei `agent/remote.py` aus dem Release auf Capella bereitstellen. In der Agent-Umgebung müssen `REMOTE_URL` und `REMOTE_AGENT_TOKEN` gesetzt sein. Die URL enthält einen etwaigen Proxy-Pfad vor `/api/v1`. Vom Release-Verzeichnis aus starten.

```sh
python3.11 agent/remote.py --state "$HOME/.claude-remote/demo-a" init \
  "$HOME/repositories/test-repo" Demo-A 'Welche Farbe?' 'Variante A freigeben?'
python3.11 agent/remote.py --state "$HOME/.claude-remote/demo-a" run
```

Für einen zweiten Job einen anderen Namen und ein anderes Zustandsverzeichnis verwenden. `run` läuft im Vordergrund und fragt alle acht Sekunden ab. Der Ordner enthält die dauerhafte Bindung zwischen Projekt, Session und Batch sowie das Journal der Entscheidungen. [Agent-Anleitung](../agent/README.md)

## 5. Auf dem iPhone antworten

In Xcode [das Projekt](../ios/ClaudeRemote.xcodeproj/project.pbxproj) öffnen, eigenes Signing-Team und Bundle-ID setzen und auf einem iPhone mit iOS 17 oder neuer starten. Dispatcher-Basis-URL und Benutzer-Token eingeben und verbinden. In „Fragen“ den Batch öffnen und alle Fragen beantworten. Nach dem Senden und der Agent-Bestätigung die Liste zum Aktualisieren herunterziehen.

Für Push die App-ID im Apple Developer Account mit Push Notifications versehen, ein passendes Provisioning Profile verwenden und den APNs-Worker mit passendem Key, Team, Topic und Sandbox- oder Produktionsumgebung starten. Auf dem iPhone „Mitteilungen aktivieren“ wählen und danach einen neuen Fragebatch erzeugen. Beim Antippen der Mitteilung soll die App die Frage über ihre authentifizierte Verbindung laden. [iOS-Anleitung](../ios/README.md) · [Backend-Anleitung](../backend/README.md)

## Fehlersuche

| Beobachtung | Prüfen |
| --- | --- |
| `/health` liefert 404 oder 502 | Basis-Pfad, Uberspace-Proxy, Dienststatus und konfigurierten Port abgleichen. |
| HTTP 401 | App verwendet das Benutzer-Token, Agent das Agent-Token. URL und zugehörige Umgebung gemeinsam prüfen. |
| Sitzung sichtbar, Frage fehlt | Der Job muss laufen und autonom sein. Agent-Ausgabe und API-Fehler prüfen. |
| Antwort wartet auf Bestätigung | Agent läuft unter demselben Zustandsordner, dieselbe Claude-Sitzung ist auf dem Host verfügbar und der Agent erreicht die API. |
| Agent meldet `interrupted during Claude Resume` | Gebundene Session und Entscheidungs-ID im Claude-Verlauf abgleichen. Das Journal behalten. Automatische Auflösung steht aus. |
| Text funktioniert, Push fehlt | iOS-Mitteilungsberechtigung, Geräteprofil, Tokenregistrierung und APNs-Worker prüfen. Sandbox, Team-ID, Key-ID und Bundle-ID müssen zur App passen. Danach einen neuen Batch erzeugen. |

Für die Abnahme zählt der passende Nachweis. Ein unsignierter Xcode-Build belegt die Kompilierung. Ein sichtbarer Batch belegt den Textabruf. Erst eine am physischen iPhone empfangene und geöffnete Mitteilung belegt die Push-Kette. [Testplan](test-plan.md)
