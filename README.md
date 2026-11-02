# README

## Top-level Schemas

* [add-realm input](./add-realm-input.md "Create the realm of a user domain, before any client registers in it") – `http://schema.nethserver.org/idp/add-realm-input.json`

* [add-realm output](./add-realm-output.md "The new realm") – `http://schema.nethserver.org/idp/add-realm-output.json`

* [alter-realm input](./alter-realm-input.md "Change the settings of a realm") – `http://schema.nethserver.org/idp/alter-realm-input.json`

* [alter-realm output](./alter-realm-output.md "Empty object") – `http://schema.nethserver.org/idp/alter-realm-output.json`

* [alter-realm-client input](./alter-realm-client-input.md "Change the settings of the client of an NS8 module") – `http://schema.nethserver.org/idp/alter-realm-client-input.json`

* [configure-module input](./configure-module-input.md "Configure idp") – `http://schema.nethserver.org/idp/configure-module-input.json`

* [get-client-access input](./get-client-access-input.md "Read the access policy of a client") – `http://schema.nethserver.org/idp/get-client-access-input.json`

* [get-configuration output](./get-configuration-output.md "Get idp configuration") – `http://schema.nethserver.org/idp/get-configuration-output.json`

* [list-realms input](./list-realms-input.md "List the realms of the idp and the clients of NS8 modules") – `http://schema.nethserver.org/idp/list-realms-input.json`

* [list-realms output](./list-realms-output.md "Realms of the idp, with the clients of NS8 modules") – `http://schema.nethserver.org/idp/list-realms-output.json`

* [register-client input](./register-client-input.md "Create or update the OIDC client of the calling module, in the realm of a user domain") – `http://schema.nethserver.org/idp/register-client-input.json`

* [register-client output](./register-client-output.md "OIDC client credentials and issuer") – `http://schema.nethserver.org/idp/register-client-output.json`

* [remove-realm input](./remove-realm-input.md "Remove a realm and unbind the idp from its user domain") – `http://schema.nethserver.org/idp/remove-realm-input.json`

## Other Schemas

### Objects

* [Untitled object in list-realms output](./list-realms-output-properties-realms-items.md) – `http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items`

* [Untitled object in list-realms output](./list-realms-output-properties-realms-items-properties-clients-items.md) – `http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items`

### Arrays

* [Untitled array in list-realms output](./list-realms-output-properties-realms.md) – `http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms`

* [Untitled array in list-realms output](./list-realms-output-properties-realms-items-properties-clients.md) – `http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients`

* [Untitled array in register-client input](./register-client-input-properties-redirect_uris.md "Redirect URIs of the authorization code flow") – `http://schema.nethserver.org/idp/register-client-input.json#/properties/redirect_uris`

* [Untitled array in register-client input](./register-client-input-properties-post_logout_redirect_uris.md "URIs where the logout redirects the user") – `http://schema.nethserver.org/idp/register-client-input.json#/properties/post_logout_redirect_uris`

* [Untitled array in register-client input](./register-client-input-properties-web_origins.md "Allowed CORS origins") – `http://schema.nethserver.org/idp/register-client-input.json#/properties/web_origins`

* [Untitled array in register-client input](./register-client-input-properties-audience.md "Client IDs added to the audience of the tokens, for example the mail module whose Dovecot introspects them") – `http://schema.nethserver.org/idp/register-client-input.json#/properties/audience`

## Version Note

The schemas linked above follow the JSON Schema Spec version: `http://json-schema.org/draft-07/schema#`
