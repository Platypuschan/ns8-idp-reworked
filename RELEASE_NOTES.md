Erste stabile Version des angepassten Identity-Provider-Moduls für NethServer 8 (Keycloak 26.8.2).

- Keycloak-Laufzeit und Provider von 26.8.1 auf 26.8.2 angehoben: enthält die Sicherheitskorrekturen des Upstream-Releases 26.8.2 (u. a. Admin-API-Audience-Prüfung, Authentifizierungs-Race, id_token_hint-Logout).
- Betriebsrichtlinien auf der Seite **Einstellungen** (Admin-Konsole nur vom Knoten, Gruppen nur aus dem Verzeichnis, Stamm-URL zur Kontoseite, strenge Anwendungsadressen), standardmäßig an.
- Client-Gruppenregel, optionale Tokenlaufzeit und Anmeldung mit Gerätezertifikat (benötigt `traefik-reworked` 4.2.5-reworked.1 oder neuer).
- Härtung: Das Einordnen der Zertifikats-Ausführung im Browser-Flow ist beschränkt und bricht mit Fehler ab, statt endlos zu laufen.

Update-Reihenfolge: Zuerst bei Nutzung der Zertifikatsanmeldung `traefik-reworked`, danach dieses Modul. Bestehende Realms, Clients und Tresordaten bleiben erhalten.

Nicht von der CI abgedeckt: `lets_encrypt=true` mit Zertifikatsanmeldung, vollständige Wiederherstellung, kompletter Bitwarden-Login mit MFA. Keine Katalogaufnahme.
