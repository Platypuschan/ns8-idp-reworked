# Untitled array in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/groups_claim
```

LDAP groups whose current memberships the tokens of the client carry in the groups claim, for example gitea-admin. Requires access_required=true. An empty list removes the claim; if the attribute is missing the current setting is kept

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## groups_claim Type

`string[]`

## groups_claim Constraints

**maximum number of items**: the maximum number of items for this array is: `32`
