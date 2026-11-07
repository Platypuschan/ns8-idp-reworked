# Vorabversion 0.1.0-rc.6 vorbereiten

Arbeitsbranch: `claude/configurable-settings` ([PR #22](https://github.com/Platypuschan/ns8-idp-reworked/pull/22)). Getesteter Anwendungsstand unverändert: Keycloak 26.8.1; keine pauschalen Abhängigkeitsupgrades. Die vorigen Abläufe sind in [RELEASE-0.1.0-rc.1.md](RELEASE-0.1.0-rc.1.md) und [RELEASE-0.1.0-rc.2.md](RELEASE-0.1.0-rc.2.md) belegt.

Nutzerfreigabe 01.11.2026 (Chat): „merge pr, veröffentlich neue versionen zum testen“.

1. PR #22 mit einem Merge-Commit nach `main` übernehmen, nicht per Squash: Vaultwarden pinnt in `IDP_REF` Branch-Commits, die dabei erreichbar bleiben müssen.
2. `Prepare prerelease` auf dem Merge-Commit von `main` manuell starten. VERSION erlaubt ausschließlich RC-Versionen.
3. Der Workflow baut Kandidaten (`candidate-<commit>`), veröffentlicht zunächst diese Testimages und referenziert die Keycloak-Runtime im Modul per Digest.
4. NS8-QEMU muss auf Debian 13 und Rocky 9 erfolgreich sein.
5. Erst nach grünen Prüfungen werden die geprüften Digests auf `0.1.0-rc.6` kopiert und ein GitHub-Prerelease mit RELEASE_NOTES.md erstellt. Vorhandene Versionstags werden nicht überschrieben. Kein `latest`, keine Katalogaufnahme und kein Produktivrollout.
6. Danach die Prüfnachweise in `docs/RELEASE-0.1.0-rc.6.md` festhalten und den Kopf der README auf „veröffentlicht“ ändern.

Vaultwarden Reworked braucht weiterhin mindestens `idp-reworked:0.1.0-rc.4`; ein Wechsel seiner Pins auf rc.6 ist eine eigene Aufgabe. Die Pakete `idp-reworked` und `idp-reworked-keycloak` sind bereits öffentlich; neue Tags erben diese Sichtbarkeit.

IdP-QEMU führt die Realm-, Gruppenregel-, Stamm-URL-, Zertifikats- und Entfernungs-Suite als Neuinstallation aus. Ein Update von 0.1.0-rc.5 prüft der Workflow nicht.

Die Release-Notizen sind keine Behauptung bereits abgeschlossener RC-Tests. Testberichte und lokale Prüfungen werden getrennt dokumentiert.
