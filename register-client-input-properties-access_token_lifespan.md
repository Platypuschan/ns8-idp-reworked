# Untitled undefined type in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/access_token_lifespan
```

Lifespan of the access tokens of the client, in seconds, for applications that need a value other than the realm default, like Vaultwarden. null restores the realm default; if the attribute is missing the current value is kept

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## access_token_lifespan Type

`integer`

## access_token_lifespan Constraints

**maximum**: the value of this number must smaller than or equal to: `86400`

**minimum**: the value of this number must greater than or equal to: `60`
