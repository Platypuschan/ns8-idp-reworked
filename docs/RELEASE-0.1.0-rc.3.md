# IdP Reworked 0.1.0-rc.3

Veröffentlicht am 27.10.2026 als Vorabversion, kein Stable-/Katalogrelease. Nutzerfreigabe 27.10.2026 (Chat): „if ci is green, merge and make rc.3“.

- [Release](https://github.com/Platypuschan/ns8-idp-reworked/releases/tag/0.1.0-rc.3)
- Geprüfter Release-Commit: ce24469f534ff89f6f8da5e5babff04f385876ed (Merge von [PR #5](https://github.com/Platypuschan/ns8-idp-reworked/pull/5): Stamm-URL → Kontoseite des Domänen-Realms).
- [Build, QEMU und Freigabe](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/40429300125): vollständig erfolgreich; Debian13 und Rocky9 jeweils 32 PASS, 1 erwarteter Upgrade-Skip, 0 FAIL, darunter beide Stamm-URL-Prüfungen. Core 3.23.2.
- Funktionstests am Branch: [Client access tests](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/40428861438) erfolgreich an 74b26ed (Unit 15, Sperre 3 mit 1 Skip, Protokoll 17 und 6 gegen Keycloak 26.7.4 und Samba AD); [NS8-QEMU am Branch](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/40427996620) an fd2474e ebenso je 32 PASS.

| Image | Digest |
| --- | --- |
| ghcr.io/platypuschan/idp-reworked:0.1.0-rc.3 | sha256:da17485ce651a43aede7bb1e06f778d26d8c030c3d6efbc7c3c7819931789856 |
| ghcr.io/platypuschan/idp-reworked-keycloak:0.1.0-rc.3 | sha256:1fb3fba23bc64c2c51c887f84bc6aa0fa00267f9313b5746a22179d4300af29d |

Beide Images anonym aus GHCR geprüft; die RC-Digests entsprechen den QEMU-geprüften Kandidaten (`candidate-ce24469f534f`). Der GitHub-Release-Text entspricht RELEASE_NOTES.md.

Vaultwarden Reworked bleibt auf `idp-reworked:0.1.0-rc.2` gepinnt; rc.3 ändert keine Schnittstelle, die Vaultwarden nutzt.

Nicht geprüft: Update einer NS8-Installation von 0.1.0-rc.2, physische Mobilgeräte, MFA-Szenarien, vollständige Cluster-Wiederherstellung.
