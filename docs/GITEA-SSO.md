# Gitea behind IdP Reworked

Status: implemented in the Gitea module
([ns8-gitea-reworked](https://github.com/Platypuschan/ns8-gitea-reworked) 0.4.20
and newer; this IdP 0.1.2 or newer for the groups claim). The module's README
section *Single sign-on with idp-reworked* is the user documentation; this
page records what the IdP side provides.

## What Gitea uses

- `register-client` with the module's own authorization
  `idp-reworked@any:clientadm`. The client ID is the module ID, the callback is
  `https://<host>/user/oauth2/ns8-sso/callback`.
- `access_required: true`. The client has no usable access policy until an
  administrator selects an LDAP group on the **Access** page
  (`alter-realm-client`, `access_group`); until then every login is refused.
  The requirement is never cleared by a later registration, so a client that
  is deleted and registered again (for example after the module lost and
  regained its user domain) comes back closed, not open.
- `groups_claim: ["<group>"]` (optional, IdP 0.1.2): the token gate adds the
  claim `groups` to ID token, access token and userinfo with the user's
  **current** LDAP memberships in the listed groups only. The memberships are
  read from LDAP for each token, never from the Keycloak user cache; without
  an LDAP-only membership read the claim is empty. Gitea maps it to
  administrator rights (`--group-claim-name groups --admin-group <group>`).

## What the IdP does not do

- It does not end sessions, personal access tokens or SSH keys that Gitea
  issued. Removing a user from the access group blocks new SSO logins and token
  issuance at the IdP only.
- It deletes the client of a module that is no longer bound to the user
  domain, together with its access group. Deleting the source in Gitea or
  switching SSO off in the module therefore does not unbind the domain.

## Deployments

One IdP instance per Gitea instance is supported by the module. A second
IdP instance with the same realm works on its own, but user IDs (`sub`)
differ between instances; accounts are linked by user name through
`ACCOUNT_LINKING=auto`, so it would need a second source and login button.
