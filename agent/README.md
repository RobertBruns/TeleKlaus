# Agent

Ein Job verwendet ein privates Zustandsverzeichnis und einen Operator-freigegebenen Projektpfad. Für den Textpfad die zwei Variablen `REMOTE_URL` und `REMOTE_AGENT_TOKEN` aus einer privaten Umgebung setzen. `REMOTE_URL` enthält die HTTPS-Basisadresse einschließlich einer etwaigen Proxy-Pfadpräfixe, ohne `/api/v1`.

```sh
python3.11 remote.py --state "$HOME/.claude-remote/demo-a" init /path/to/test-repo Demo-A 'Welche Farbe?' 'Variante A freigeben?'
python3.11 remote.py --state "$HOME/.claude-remote/demo-a" run
```

Ein zweiter Job erhält einen eigenen Namen und ein eigenes Zustandsverzeichnis. `init` ist der explizite autonome Opt-in und erfasst von Claude zurückgegebene Operatorfragen. Resume verwendet dieselbe Claude-ID, denselben Projektpfad und als Standardeingabe kodiertes JSON. Der Agent speichert bestätigte Entscheidungen vor dem API-Ack. Wiederholte Antworten nach einem Netzwerkfehler triggern dadurch keinen zweiten Claude-Turn. Stürzt der Prozess während Claude Resume ab, verbleibt die Entscheidung in `processing` und erfordert einen Abgleich des gebundenen Transkripts. Der Agent startet in diesem Fall keinen zweiten Turn.

Der vorliegende Job unterstützt einen Fragebatch und nutzt Claude mit deaktivierten Tools. Eingriff in interaktive Sitzungen, Skills/Hooks für modellinitiierte Fragen und eine automatische Wiederaufnahme bei unklarer Ausführung sind offen.
