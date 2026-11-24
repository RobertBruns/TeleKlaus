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

Braucht Claude eine Entscheidung, landet ein Fragebatch auf dem Telefon. `tk-claude` wartet ohne laufenden Claude-Prozess und setzt nach der Antwort dieselbe Session fort. Am Ende gibt es Claudes Ergebnis aus und meldet `complete`. Fehler und eine überschrittene Wartezeit melden `error` und enden mit Exit-Code ungleich 0, bei Zeitüberschreitung 3. Optionen vor `-p`: `--tk-name NAME` (Anzeige in der App, Standard Ordnername) und `--tk-wait 8h` (Standard). Zugang aus `~/.config/teleklaus/agent.env` oder `TK_ENV_FILE`. Protokoll je Lauf unter `~/.claude-remote/tk/<session>/journal.jsonl`.

Claude fragt verlässlich nur, wenn der Prompt sagt, worüber. Ohne Vorgabe wählt es plausible Standards und nennt sie im Ergebnis. Stürzt `tk-claude` während des Wartens ab, wird eine spätere Antwort nicht mehr zugestellt. Eine automatische Wiederaufnahme fehlt.
