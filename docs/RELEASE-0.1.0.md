# Release 0.1.0 (stabil)

Veröffentlicht am 08.11.2026 auf Nutzerauftrag (Chat): Review, offene PRs mergen, stabile Version veröffentlichen. Keine Katalogaufnahme, kein Rollout auf Nutzerinstanzen.

- Release: [0.1.0](https://github.com/Platypuschan/ns8-idp-reworked/releases/tag/0.1.0), Commit d658c9d2ac068aea69eb3a4fe12375bd4f212bae
- Lauf: [42482248590](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/42482248590), Debian 13 und Rocky 9 erfolgreich
- `ghcr.io/platypuschan/idp-reworked:0.1.0`: `sha256:74632c65ce96aef543a99545ae46fee0f9dcd6e358e9414d6c2e2b55ecd3e377`
- `ghcr.io/platypuschan/idp-reworked-keycloak:0.1.0`: `sha256:102234da48dcf6074de6d648ce07db7f1f22aa4fb98d9660789364e04099a10b`

## Änderungen gegenüber main 3d6bb32

- Keycloak 26.8.1 → 26.8.2 (Sicherheitsrelease).
- Keycloak 26.8.2 verlangt für Admin-API-Tokens den Scope `kc-admin-api` (CVE-2026-19688). `keycloak-init` weist ihn `ns8-agent` zu; `update-module.d/60agent-scope` setzt alte Zugangsdaten zurück, damit bestehende Installationen beim Update repariert werden. Erster Release-Lauf scheiterte daran mit HTTP 401 (nichts veröffentlicht).
- Begrenzte Schleife beim Einordnen der Zertifikats-Ausführung.
- Workflow akzeptiert stabile Versionen; Release wird dann als „Latest“ markiert.

## Grenzen

Update von einer bestehenden Installation (rc.5 oder Kandidat) ist in der CI nicht geprüft; es gab keine stabile Vorversion für das Update-Szenario. Nicht geprüft: `lets_encrypt=true` mit Zertifikatsanmeldung, vollständige Wiederherstellung, kompletter Bitwarden-Login mit MFA.
