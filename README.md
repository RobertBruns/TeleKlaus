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

Stand 24. November 2026. Der Dispatcher läuft unter `https://teleklaus.rand.uber.space`. Eine auf dem iPhone beantwortete Frage wurde über Styx und den Agenten auf Capella derselben Claude-Sitzung zugestellt und bestätigt. Eine Push-Mitteilung kam auf dem iPhone an und öffnete den Fragebatch.
# TeleKlaus
