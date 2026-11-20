# Untitled boolean in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/access_required
```

Require a client access group even if its policy is removed. Once enabled, registration never clears this requirement.

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## access_required Type

`boolean`

## access_required Default Value

The default value is:

```json
false
```
