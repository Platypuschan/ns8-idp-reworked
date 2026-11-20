# Untitled object in list-realms output Schema

```txt
http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items
```



| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                      |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-realms-output.json\*](idp/list-realms-output.json "open original schema") |

## items Type

`object` ([Details](list-realms-output-properties-realms-items-properties-clients-items.md))

# items Properties

| Property                      | Type      | Required | Nullable       | Defined by                                                                                                                                                                                                                                                |
| :---------------------------- | :-------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [client_id](#client_id)       | `string`  | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-client_id.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/client_id")       |
| [enabled](#enabled)           | `boolean` | Required | cannot be null | [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-enabled.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/enabled")           |
| [access_group](#access_group) | `string`  | Optional | can be null    | [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-access_group.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/access_group") |

## client_id

Module ID, owner of the client

`client_id`

* is required

* Type: `string`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-client_id.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/client_id")

### client_id Type

`string`

## enabled



`enabled`

* is required

* Type: `boolean`

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-enabled.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/enabled")

### enabled Type

`boolean`

## access_group

LDAP group whose members can sign in to the client, or null if the client is not restricted. The group is null also if the restriction refers to a removed group: then nobody can sign in

`access_group`

* is optional

* Type: `string`

* can be null

* defined in: [list-realms output](list-realms-output-properties-realms-items-properties-clients-items-properties-access_group.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/access_group")

### access_group Type

`string`
