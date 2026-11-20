# Untitled string in get-client-access input Schema

```txt
http://schema.nethserver.org/idp/get-client-access-input.json#/properties/domain
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [get-client-access-input.json\*](idp/get-client-access-input.json "open original schema") |

## domain Type

`string`

## domain Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z0-9.-]+$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z0-9.-%5D%2B%24 "try regular expression with regexr.com")
