Fünfte Vorabversion des angepassten Identity-Provider-Moduls für NethServer 8. Neue Funktion: optionale Anmeldung mit Gerätezertifikat.

- Bestehende Domänenbenutzer können sich nach einmaliger Einrichtung ohne Passwort anmelden. Nur das öffentliche Zertifikat wird registriert, der private Schlüssel bleibt auf dem Gerät. Die Funktion ist pro Realm abschaltbar und standardmäßig aus.
- Voraussetzung ist die Clientzertifikats-Erweiterung für NS8-Traefik aus `integrations/ns8-traefik`. Das Standard-Traefik kann die Funktion nicht aktivieren. Für alle anderen Anwendungen und die Passwortanmeldung ändert sich nichts.
- Gesperrte Konten bleiben gesperrt: Deaktivierte oder abgelaufene AD-Konten, gesperrte OpenLDAP-Konten und entzogene Gruppen verweigern die Zertifikatsanmeldung. Ist der Kontostatus nicht lesbar, wird abgelehnt.
- Das Zertifikat ersetzt den Passwort-/OTP-Zweig und ist kein zweiter Faktor. Fordert eine Anwendung eine neue Anmeldung an (`prompt=login`, `max_age`), erscheint das Passwortformular.
- Ein Widerruf beendet alle IdP-Sitzungen des Benutzers. Bestehende Anwendungssitzungen und Offline-Daten behalten ihre eigene Lebensdauer.
- Ersetzt ein Traefik-Update die Erweiterung, zeigt die Seite **Zertifikate** eine Warnung; die Passwortanmeldung funktioniert weiter.
- Beim Aktivieren oder Deaktivieren ist die IdP-Adresse kurz nicht erreichbar.
- Updates behalten jetzt die Let's-Encrypt-Einstellung der Admin-Route.

Keine Stable- oder Katalogfreigabe; Vorabversion für Testinstallationen. Geprüft im NS8-Test (Debian 13, Rocky 9) mit der Traefik-Erweiterung in Wegwerf-VMs. Physisch auf einem Android-13-Tablet geprüft: Chrome, Custom Tab und WebView mit einer eigenen Test-App, vor den letzten Korrekturen. Nicht abgedeckt sind `lets_encrypt=true` mit Zertifikatsanmeldung, das echte Update von rc.4 mit aktiver Funktion, die vollständige Wiederherstellung, der komplette Bitwarden-Login und MFA.
