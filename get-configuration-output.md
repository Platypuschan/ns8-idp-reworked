# get-configuration output Schema

```txt
http://schema.nethserver.org/idp/get-configuration-output.json
```

Get idp configuration

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [get-configuration-output.json](idp/get-configuration-output.json "open original schema") |

## get-configuration output Type

`object` ([get-configuration output](get-configuration-output.md))

## get-configuration output Examples

```json
{
  "host": "sso.example.org",
  "lets_encrypt": true
}
```

# get-configuration output Properties

| Property                                          | Type      | Required | Nullable       | Defined by                                                                                                                                                                                    |
| :------------------------------------------------ | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [host](#host)                                     | `string`  | Required | cannot be null | [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/host")                                     |
| [lets_encrypt](#lets_encrypt)                     | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/lets_encrypt")                     |
| [restrict_admin_console](#restrict_admin_console) | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-restrict_admin_console.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/restrict_admin_console") |
| [directory_groups_only](#directory_groups_only)   | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-directory_groups_only.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/directory_groups_only")   |
| [account_home_redirect](#account_home_redirect)   | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-account_home_redirect.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/account_home_redirect")   |
| [strict_client_uris](#strict_client_uris)         | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-strict_client_uris.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/strict_client_uris")         |

## host

Host name of the identity provider. Empty if the module is not configured yet

`host`

* is required

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/host")

### host Type

`string`

## lets_encrypt

A Let's Encrypt certificate is requested for the host name

`lets_encrypt`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/lets_encrypt")

### lets_encrypt Type

`boolean`

## restrict_admin_console

Allow the Keycloak admin console from the node only

`restrict_admin_console`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-restrict_admin_console.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/restrict_admin_console")

### restrict_admin_console Type

`boolean`

## directory_groups_only

Ignore local Keycloak group memberships. Required by client access policies

`directory_groups_only`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-directory_groups_only.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/directory_groups_only")

### directory_groups_only Type

`boolean`

## account_home_redirect

Lead the host root to the account console instead of the admin console

`account_home_redirect`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-account_home_redirect.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/account_home_redirect")

### account_home_redirect Type

`boolean`

## strict_client_uris

Accept only exact HTTPS or native client endpoints at client registration

`strict_client_uris`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-strict_client_uris.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/strict_client_uris")

### strict_client_uris Type

`boolean`
