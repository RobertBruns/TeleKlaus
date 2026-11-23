# Sicherheitsgrenzen

Dispatcher und Agent verwenden getrennte Bearer-Tokens. Die aktuelle Installation ist für einen Betreiber und einen Entwicklungsaccount konzipiert. Datenbankabfragen binden Agent-Sitzungen an Tenant und Host. Benutzerzugriff ist auf denselben konfigurierten Tenant und Host beschränkt. Vor Mehrmandantenbetrieb sind getrennte Identitäten, Rate Limits, Widerruf und Isolationsprüfungen erforderlich.

Der Agent lehnt HTTP und Redirects ab. Antworten gehen als JSON über stdin in einen fixen Claude-Aufruf. Werkzeuge und lokale Anpassungen sind im Demo deaktiviert. Keine SSH- oder APNs-Schlüssel in die App-Konfiguration aufnehmen. Den Stand der persistenten Datenbank und die Konfiguration gemeinsam sichern. Das Weiterreichen an APNs enthält keine Projekt- oder Frageinformationen.
