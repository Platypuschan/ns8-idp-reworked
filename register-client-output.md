# register-client output Schema

```txt
http://schema.nethserver.org/idp/register-client-output.json
```

OIDC client credentials and issuer

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [register-client-output.json](idp/register-client-output.json "open original schema") |

## register-client output Type

`object` ([register-client output](register-client-output.md))

## register-client output Examples

```json
{
  "client_id": "nextcloud1",
  "client_secret": "2Gv4...",
  "realm": "dp.example.org",
  "issuer": "https://sso.example.org/realms/dp.example.org"
}
```

# register-client output Properties

| Property                        | Type     | Required | Nullable       | Defined by                                                                                                                                                            |
| :------------------------------ | :------- | :------- | :------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [client_id](#client_id)         | `string` | Required | cannot be null | [register-client output](register-client-output-properties-client_id.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/client_id")         |
| [client_secret](#client_secret) | `string` | Required | cannot be null | [register-client output](register-client-output-properties-client_secret.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/client_secret") |
| [realm](#realm)                 | `string` | Required | cannot be null | [register-client output](register-client-output-properties-realm.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/realm")                 |
| [issuer](#issuer)               | `string` | Required | cannot be null | [register-client output](register-client-output-properties-issuer.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/issuer")               |

## client_id



`client_id`

* is required

* Type: `string`

* cannot be null

* defined in: [register-client output](register-client-output-properties-client_id.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/client_id")

### client_id Type

`string`

## client_secret



`client_secret`

* is required

* Type: `string`

* cannot be null

* defined in: [register-client output](register-client-output-properties-client_secret.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/client_secret")

### client_secret Type

`string`

## realm



`realm`

* is required

* Type: `string`

* cannot be null

* defined in: [register-client output](register-client-output-properties-realm.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/realm")

### realm Type

`string`

## issuer

OIDC issuer URL of the realm

`issuer`

* is required

* Type: `string`

* cannot be null

* defined in: [register-client output](register-client-output-properties-issuer.md "http://schema.nethserver.org/idp/register-client-output.json#/properties/issuer")

### issuer Type

`string`
