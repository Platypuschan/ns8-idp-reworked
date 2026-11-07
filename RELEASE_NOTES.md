Sechste Vorabversion des angepassten Identity-Provider-Moduls für NethServer 8. Neu sind Betriebsrichtlinien auf der Seite **Einstellungen**.

- Vier Schalter: Admin-Konsole nur vom Knoten, Gruppenmitgliedschaften nur aus dem Verzeichnis, Stamm-URL führt zur Kontoseite, strenge Anwendungsadressen. Alle sind standardmäßig an, bestehende Installationen ändern sich also nicht.
- „Nur aus dem Verzeichnis" lässt sich nicht abschalten, solange Zugriffsregeln bestehen.
- Die Zertifikatsanmeldung braucht jetzt das Modul `traefik-reworked` statt manuell eingespielter Dateien.

Update-Reihenfolge: Zuerst `api-cli run cluster/update-module --data '{"module_url":"ghcr.io/platypuschan/traefik-reworked:4.2.5-reworked.1","instances":["traefik1"]}'`, aber nur wenn die Zertifikatsanmeldung genutzt werden soll. Danach das IdP-Modul.

Keine Stable- oder Katalogfreigabe; Vorabversion für Testinstallationen. Geprüft im NS8-Test (Debian 13, Rocky 9). Nicht abgedeckt sind `lets_encrypt=true` mit Zertifikatsanmeldung, das echte Update von rc.5, die vollständige Wiederherstellung, der komplette Bitwarden-Login und MFA.
