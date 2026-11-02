# Untitled object in list-realms output Schema

```txt
http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-realms-output.json\*](idp/list-realms-output.json "open original schema") |

## items Type

`object` ([Details](list-realms-output-properties-realms-items.md))

# items Properties

| Property                                | Type      | Required | Nullable       | Defined by                                                                                                                                                                                                        |
| :-------------------------------------- | :-------- | :------- | :------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [name](#name)                           | `string`  | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-name.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/name")                           |
| [enabled](#enabled)                     | `boolean` | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-enabled.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/enabled")                     |
| [issuer](#issuer)                       | `string`  | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-issuer.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/issuer")                       |
| [user_domain_found](#user_domain_found) | `boolean` | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-user_domain_found.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/user_domain_found") |
| [clients](#clients)                     | `array`   | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-clients.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients")                     |

## name

Realm name, which is also the user domain name

`name`

* is required

* Type: `string`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-name.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/name")

### name Type

`string`

## enabled



`enabled`

* is required

* Type: `boolean`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-enabled.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/enabled")

### enabled Type

`boolean`

## issuer

OIDC issuer URL

`issuer`

* is required

* Type: `string`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-issuer.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/issuer")

### issuer Type

`string`

## user_domain_found

False if the user domain of the realm was removed from the cluster

`user_domain_found`

* is required

* Type: `boolean`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-user_domain_found.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/user_domain_found")

### user_domain_found Type

`boolean`

## clients



`clients`

* is required

* Type: `object[]` ([Details](list-realms-output-properties-realms-items-properties-clients-items.md))

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-clients.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients")

### clients Type

`object[]` ([Details](list-realms-output-properties-realms-items-properties-clients-items.md))
