# Claude Remote

Claude Remote soll dir Entscheidungen aus laufenden Claude-Code-Aufgaben aufs iPhone bringen. Der aktuelle Prototyp zeigt den Textweg: Eine verwaltete Claude-Sitzung stellt eine Frage, du antwortest, und genau diese Sitzung wird mit deiner Entscheidung fortgesetzt.

**Einsteigen** · [ELI5 mit Beispiel und Bilderbuchablauf](docs/eli5.md)

**Ausprobieren** · [Schritt für Schritt von der lokalen Prüfung zum iPhone](docs/betrieb.md)

**Nachschlagen** · [Machbarkeit](docs/feasibility.md) · [Architektur](docs/architecture.md) · [API](docs/api/openapi.yaml) · [Sicherheit](docs/security.md) · [Testnachweise](docs/test-plan.md) · [Offene Sprachmessungen](docs/voice-benchmarks.md)

| Bestandteil | Ablage | Aufgabe |
| --- | --- | --- |
| Dispatcher | [backend/](backend/README.md) | Speichert Sitzungen, Fragen, Antworten, Quittungen und Push-Aufträge |
| Agent | [agent/](agent/README.md) | Bindet eine Entscheidung an die richtige Claude-Sitzung und bestätigt die Fortsetzung |
| App | [ios/](ios/README.md) | Zeigt Sitzungen, Fragebatches und Verlauf. Erfasst Text und Freigaben |
| Projektübergabe | [handoff.md](handoff.md) | Hält Stand und nächste Prüfpunkte fest |

Stand 21. November 2026. Beide Uberspace-Accounts sind inventarisiert. Der Resume-Test über beide Hosts, der kombinierte Test mit zwei echten Claude-Sitzungen und der unsignierte iPhone-Build waren erfolgreich. Der installierte HTTPS-Betrieb und die Push-Zustellung auf einem signierten iPhone sind offen.
# TeleKlaus
