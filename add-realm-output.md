# add-realm output Schema

```txt
http://schema.nethserver.org/idp/add-realm-output.json
```

The new realm

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [add-realm-output.json](idp/add-realm-output.json "open original schema") |

## add-realm output Type

`object` ([add-realm output](add-realm-output.md))

## add-realm output Examples

```json
{
  "name": "dp.example.org",
  "issuer": "https://sso.example.org/realms/dp.example.org"
}
```

# add-realm output Properties

| Property          | Type     | Required | Nullable       | Defined by                                                                                                                            |
| :---------------- | :------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------ |
| [name](#name)     | `string` | Required | cannot be null | [add-realm output](add-realm-output-properties-name.md "http://schema.nethserver.org/idp/add-realm-output.json#/properties/name")     |
| [issuer](#issuer) | `string` | Required | cannot be null | [add-realm output](add-realm-output-properties-issuer.md "http://schema.nethserver.org/idp/add-realm-output.json#/properties/issuer") |

## name



`name`

* is required

* Type: `string`

* cannot be null

* defined in: [add-realm output](add-realm-output-properties-name.md "http://schema.nethserver.org/idp/add-realm-output.json#/properties/name")

### name Type

`string`

## issuer

OIDC issuer URL

`issuer`

* is required

* Type: `string`

* cannot be null

* defined in: [add-realm output](add-realm-output-properties-issuer.md "http://schema.nethserver.org/idp/add-realm-output.json#/properties/issuer")

### issuer Type

`string`
