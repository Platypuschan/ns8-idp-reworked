# configure-module input Schema

```txt
http://schema.nethserver.org/idp/configure-module-input.json
```

Configure idp

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [configure-module-input.json](idp/configure-module-input.json "open original schema") |

## configure-module input Type

`object` ([configure-module input](configure-module-input.md))

## configure-module input Examples

```json
{
  "host": "sso.example.org",
  "lets_encrypt": true
}
```

# configure-module input Properties

| Property                                          | Type      | Required | Nullable       | Defined by                                                                                                                                                                              |
| :------------------------------------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)                                     | `string`  | Required | cannot be null | [configure-module input](configure-module-input-properties-host.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/host")                                     |
| [lets_encrypt](#lets_encrypt)                     | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-lets_encrypt.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/lets_encrypt")                     |
| [restrict_admin_console](#restrict_admin_console) | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-restrict_admin_console.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/restrict_admin_console") |
| [directory_groups_only](#directory_groups_only)   | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-directory_groups_only.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/directory_groups_only")   |
| [account_home_redirect](#account_home_redirect)   | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-account_home_redirect.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/account_home_redirect")   |
| [strict_client_uris](#strict_client_uris)         | `boolean` | Optional | cannot be null | [configure-module input](configure-module-input-properties-strict_client_uris.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/strict_client_uris")         |

## host

Host name of the identity provider, like sso.example.org

`host`

* is required

* Type: `string`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-host.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/host")

### host Type

`string`

### host Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
\.
```

[try pattern](https://regexr.com/?expression=%5C. "try regular expression with regexr.com")

**hostname**: the string must be a hostname, according to [RFC 1123, section 2.1](https://tools.ietf.org/html/rfc1123 "check the specification")

## lets_encrypt

Request a Let's Encrypt certificate for the host name

`lets_encrypt`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-lets_encrypt.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/lets_encrypt")

### lets_encrypt Type

`boolean`

### lets_encrypt Default Value

The default value is:

```json
false
```

## restrict_admin_console

Allow the Keycloak admin console from the node only

`restrict_admin_console`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-restrict_admin_console.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/restrict_admin_console")

### restrict_admin_console Type

`boolean`

## directory_groups_only

Ignore local Keycloak group memberships. Required by client access policies

`directory_groups_only`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-directory_groups_only.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/directory_groups_only")

### directory_groups_only Type

`boolean`

## account_home_redirect

Lead the host root to the account console instead of the admin console

`account_home_redirect`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-account_home_redirect.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/account_home_redirect")

### account_home_redirect Type

`boolean`

## strict_client_uris

Accept only exact HTTPS or native client endpoints at client registration

`strict_client_uris`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [configure-module input](configure-module-input-properties-strict_client_uris.md "http://schema.nethserver.org/idp/configure-module-input.json#/properties/strict_client_uris")

### strict_client_uris Type

`boolean`
