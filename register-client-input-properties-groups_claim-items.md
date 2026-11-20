# Untitled string in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/groups_claim/items
```



| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## items Type

`string`

## items Constraints

**maximum length**: the maximum number of characters for this string is: `128`

**minimum length**: the minimum number of characters for this string is: `1`

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[^/,\r\n]+$
```

[try pattern](https://regexr.com/?expression=%5E%5B%5E%2F%2C%5Cr%5Cn%5D%2B%24 "try regular expression with regexr.com")
