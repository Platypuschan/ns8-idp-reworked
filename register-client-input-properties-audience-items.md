# Untitled string in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/audience/items
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## items Type

`string`

## items Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z0-9_.-]+$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z0-9_.-%5D%2B%24 "try regular expression with regexr.com")
