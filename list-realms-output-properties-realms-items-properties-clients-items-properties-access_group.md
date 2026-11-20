# Untitled undefined type in list-realms output Schema

```txt
http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms/items/properties/clients/items/properties/access_group
```

LDAP group whose members can sign in to the client, or null if the client is not restricted. The group is null also if the restriction refers to a removed group: then nobody can sign in

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                      |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [list-realms-output.json\*](idp/list-realms-output.json "open original schema") |

## access_group Type

`string`
