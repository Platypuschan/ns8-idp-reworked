# Untitled undefined type in alter-realm-client input Schema

```txt
http://schema.nethserver.org/idp/alter-realm-client-input.json#/properties/access_group
```

Only the current members of this LDAP group of the user domain can sign in to the client, also with an existing SSO session or through a federated IdP. null removes the restriction. Registering the client again does not change it

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                  |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [alter-realm-client-input.json\*](idp/alter-realm-client-input.json "open original schema") |

## access_group Type

`string`

## access_group Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[^/
]+$
```

[try pattern](https://regexr.com/?expression=%5E%5B%5E%2F%0D%0A%5D%2B%24 "try regular expression with regexr.com")
