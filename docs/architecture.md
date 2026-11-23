# Textarchitektur

Der SwiftUI-Client fragt Sessions, Batches und Ereignisse ab. Der Dispatcher persistiert Batch, Entscheidung, Event und Push-Auftrag transaktional. Der Agent verbindet sich ausgehend zur API und prüft die lokale Session-Bindung vor Zustellung. Bestätigung wird zuerst im lokalen Journal, danach im Dispatcher gespeichert. Bei unklarer Ausführung hält der Agent an.

Siehe [Machbarkeit und Entscheidungen](feasibility.md), [Sicherheit](security.md) und [Testplan](test-plan.md).
