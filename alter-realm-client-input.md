# alter-realm-client input Schema

```txt
http://schema.nethserver.org/idp/alter-realm-client-input.json
```

Change the settings of the client of an NS8 module

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [alter-realm-client-input.json](idp/alter-realm-client-input.json "open original schema") |

## alter-realm-client input Type

`object` ([alter-realm-client input](alter-realm-client-input.md))

## alter-realm-client input Examples

```json
{
  "domain": "dp.example.org",
  "client_id": "nextcloud1",
  "enabled": false
}
```

```json
{
  "domain": "ad.example.org",
  "client_id": "vaultwarden1",
  "access_group": "services_vaultwarden"
}
```

```json
{
  "domain": "ad.example.org",
  "client_id": "vaultwarden1",
  "access_group": null
}
```

# alter-realm-client input Properties

| Property                      | Type      | Required | Nullable       | Defined by                                                                                                                                                                |
| :---------------------------- | :-------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [domain](#domain)             | `string`  | Required | cannot be null | [alter-realm-client input](alter-realm-client-input-properties-domain.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/domain")             |
| [client_id](#client_id)       | `string`  | Required | cannot be null | [alter-realm-client input](alter-realm-client-input-properties-client_id.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/client_id")       |
| [enabled](#enabled)           | `boolean` | Optional | cannot be null | [alter-realm-client input](alter-realm-client-input-properties-enabled.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/enabled")           |
| [access_group](#access_group) | `string`  | Optional | can be null    | [alter-realm-client input](alter-realm-client-input-properties-access_group.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/access_group") |

## domain

User domain, which is also the realm name

`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [alter-realm-client input](alter-realm-client-input-properties-domain.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**minimum length**: the minimum number of characters for this string is: `1`

## client_id

Module ID, owner of the client

`client_id`

* is required

* Type: `string`

* cannot be null

* defined in: [alter-realm-client input](alter-realm-client-input-properties-client_id.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/client_id")

### client_id Type

`string`

### client_id Constraints

**minimum length**: the minimum number of characters for this string is: `1`

## enabled

A disabled client cannot log users in. Registering the client again does not enable it

`enabled`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [alter-realm-client input](alter-realm-client-input-properties-enabled.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/enabled")

### enabled Type

`boolean`

## access_group

Only the current members of this LDAP group of the user domain can sign in to the client, also with an existing SSO session or through a federated IdP. null removes the restriction. Registering the client again does not change it

`access_group`

* is optional

* Type: `string`

* can be null

* defined in: [alter-realm-client input](alter-realm-client-input-properties-access_group.md "http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/access_group")

### access_group Type

`string`

### access_group Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[^/
]+$
```

[try pattern](https://regexr.com/?expression=%5E%5B%5E%2F%0D%0A%5D%2B%24 "try regular expression with regexr.com")
