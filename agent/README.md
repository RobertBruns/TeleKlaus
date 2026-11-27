# Agent

Ein Job verwendet ein privates Zustandsverzeichnis und einen Operator-freigegebenen Projektpfad. Für den Textpfad die zwei Variablen `REMOTE_URL` und `REMOTE_AGENT_TOKEN` aus einer privaten Umgebung setzen. `REMOTE_URL` enthält die HTTPS-Basisadresse einschließlich einer etwaigen Proxy-Pfadpräfixe, ohne `/api/v1`.

```sh
python3.11 remote.py --state "$HOME/.claude-remote/demo-a" init /path/to/test-repo Demo-A 'Welche Farbe?' 'Variante A freigeben?'
python3.11 remote.py --state "$HOME/.claude-remote/demo-a" run
```

Ein zweiter Job erhält einen eigenen Namen und ein eigenes Zustandsverzeichnis. `init` ist der explizite autonome Opt-in und erfasst von Claude zurückgegebene Operatorfragen. Resume verwendet dieselbe Claude-ID, denselben Projektpfad und als Standardeingabe kodiertes JSON. Der Agent speichert bestätigte Entscheidungen vor dem API-Ack. Wiederholte Antworten nach einem Netzwerkfehler triggern dadurch keinen zweiten Claude-Turn. Stürzt der Prozess während Claude Resume ab, verbleibt die Entscheidung in `processing` und erfordert einen Abgleich des gebundenen Transkripts. Der Agent startet in diesem Fall keinen zweiten Turn.

Der vorliegende Job unterstützt einen Fragebatch und nutzt Claude mit deaktivierten Tools. Eingriff in interaktive Sitzungen, Skills/Hooks für modellinitiierte Fragen und eine automatische Wiederaufnahme bei unklarer Ausführung sind offen.

## Skripte und geplante Aufgaben: `tk-claude`

`tk_claude.py` ersetzt `claude -p` in unbeaufsichtigten Skripten. Einmalig `ln -s "$PWD/agent/tk_claude.py" ~/bin/tk-claude` anlegen. Im Skript `claude -p "PROMPT" …` durch `tk-claude -p "PROMPT" …` ersetzen. `-p` und der Prompt müssen die ersten Argumente sein. Alle weiteren Optionen wie `--allowedTools` oder `--max-turns` gehen unverändert an Claude. `--output-format`, `--json-schema`, `--append-system-prompt`, `--session-id` und `--resume` setzt `tk-claude` selbst.

Braucht Claude eine Entscheidung, landet ein Fragebatch auf dem Telefon. `tk-claude` wartet ohne laufenden Claude-Prozess und setzt nach der Antwort dieselbe Session fort. Am Ende gibt es Claudes Ergebnis aus, meldet `complete` und schließt die Session, sodass sie aus der Liste der App verschwindet (`GET /sessions?all=true` zeigt sie weiter). Fehler und eine überschrittene Wartezeit melden `error` und enden mit Exit-Code ungleich 0, bei Zeitüberschreitung 3. Optionen vor `-p`: `--tk-name NAME` (Anzeige in der App, Standard Ordnername) und `--tk-wait 8h` (Standard). Zugang aus `~/.config/teleklaus/agent.env` oder `TK_ENV_FILE`. Protokoll je Lauf unter `~/.claude-remote/tk/<session>/journal.jsonl`.

Claude fragt verlässlich nur, wenn der Prompt sagt, worüber. Ohne Vorgabe wählt es plausible Standards und nennt sie im Ergebnis. Stürzt `tk-claude` während des Wartens ab, setzt `tk-claude [--tk-wait 8h] --tk-resume <session>` die Wartezeit auf die offene Frage fort, mit Ordner, Optionen und Name aus dem Protokoll. Stand es gerade mitten in der Fortsetzung von Claude, hält es an: dann zuerst das Claude-Transkript prüfen. Antwortet der Dispatcher mit einem HTTP-Fehler, bricht `tk-claude` sofort ab, nur Netzwerkfehler werden bis zum Ende der Wartezeit wiederholt.

## Laufende Sessions: `tk-notify`

`tk_notify.py` ist ein Notification-Hook für Claude Code. Er meldet dem Dispatcher, wenn eine Session auf dem Host auf den Operator wartet (`notification_type` `permission_prompt`, also Fragen und Freigaben). Der Dispatcher speichert das als Ereignis `attention` mit kurzem Text und schickt einen Push. Geantwortet wird weiter in der Claude-App. Der Hook schreibt nichts in die Session.

Einrichtung auf Capella: `ln -s "$PWD/agent/tk_notify.py" ~/bin/tk-notify` und in `~/.claude/settings.json` unter `hooks.Notification` einen Eintrag mit `"matcher": "permission_prompt"` und dem Befehl `"$HOME/bin/tk-notify"` (`"async": true`) anlegen. Zugang wie bei `tk-claude`. Fehler landen in `~/.claude-remote/tk-notify.log`, die Session läuft immer weiter. Der Hook kennt nur die Meldung von Claude Code, nicht den Fragetext.
