# Release 0.1.0-rc.5

Vorabversion, veröffentlicht am 31.10.2026. Nutzerfreigabe (Chat): „wenn ci grün ist, merge und mach rc.5“. Keine Stable- oder Katalogfreigabe, kein Rollout auf Nutzerinstanzen.

- Release: [0.1.0-rc.5](https://github.com/Platypuschan/ns8-idp-reworked/releases/tag/0.1.0-rc.5)
- Commit: 9f789a4ba5712d5a3f45ca17169002d2a27068b9 (Merge von PR #20; PR #19: 10382ce)
- Lauf: [41218265221](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41218265221), Debian 13 und Rocky 9 je 40 PASS + 1 erwarteter Skip, einschließlich gepatchtem Proxy in Wegwerf-VMs

## Image-Digests

Anonym geprüft, identisch mit den getesteten Kandidaten `candidate-9f789a4ba571`:

- `ghcr.io/platypuschan/idp-reworked:0.1.0-rc.5`: `sha256:d1c110c7634ef3fba879eb3c35662bf09a4f8082f66902ee9668f936b688477d`
- `ghcr.io/platypuschan/idp-reworked-keycloak:0.1.0-rc.5`: `sha256:b58df24bbd146455e0abe794edbe7fca6808f58c7a8c6accd650582915c8a30c`

Das Modul-Label `org.nethserver.images` pinnt die Keycloak-Runtime auf denselben Digest.

## Vorgeschichte

Der erste Release-Lauf [41215541043](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41215541043) an 10382ce scheiterte auf Rocky 9, weil parallele `set-route`-Tasks sich störten. Veröffentlicht wurde dabei nichts. PR #20 schreibt die Routen nacheinander und erweitert das Traefik-Patch um `29waitsync`.

## Grenzen

Nicht geprüft: `lets_encrypt=true` mit Zertifikatsanmeldung, echtes Update von rc.4, vollständige Wiederherstellung, kompletter Bitwarden-Login, MFA, Dauer des Ausfalls beim Aktivieren. Der physische Android-Test stammt aus der Zeit vor den Review-Korrekturen. Weitere Nachweise: [CERTIFICATE-VALIDATION.md](CERTIFICATE-VALIDATION.md).
