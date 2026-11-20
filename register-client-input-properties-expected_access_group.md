# Untitled string in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/expected_access_group
```

The consuming module expects this LDAP group. Resolve and pin its stable group ID independently of later administrator policy edits. Requires access_required=true.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## expected_access_group Type

`string`

## expected_access_group Constraints

**maximum length**: the maximum number of characters for this string is: `128`

**minimum length**: the minimum number of characters for this string is: `1`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[^/\r\n]+$
```

[try pattern](https://regexr.com/?expression=%5E%5B%5E%2F%5Cr%5Cn%5D%2B%24 "try regular expression with regexr.com")
