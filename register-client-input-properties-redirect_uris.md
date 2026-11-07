# Untitled array in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/redirect_uris
```

Redirect URIs of the authorization code flow. Without redirect URIs the client can only authenticate its own requests, for example token introspection

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## redirect_uris Type

`string[]`

## redirect_uris Default Value

The default value is:

```json
[]
```
