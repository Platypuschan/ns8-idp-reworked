# get-configuration output Schema

```txt
http://schema.nethserver.org/idp/get-configuration-output.json
```

Get idp configuration

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                                |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [get-configuration-output.json](idp/get-configuration-output.json "open original schema") |

## get-configuration output Type

`object` ([get-configuration output](get-configuration-output.md))

## get-configuration output Examples

```json
{
  "host": "sso.example.org",
  "lets_encrypt": true
}
```

# get-configuration output Properties

| Property                      | Type      | Required | Nullable       | Defined by                                                                                                                                                                |
| :---------------------------- | :-------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [host](#host)                 | `string`  | Required | cannot be null | [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/host")                 |
| [lets_encrypt](#lets_encrypt) | `boolean` | Required | cannot be null | [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/lets_encrypt") |

## host

Host name of the identity provider. Empty if the module is not configured yet

`host`

* is required

* Type: `string`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-host.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/host")

### host Type

`string`

## lets_encrypt

A Let's Encrypt certificate is requested for the host name

`lets_encrypt`

* is required

* Type: `boolean`

* cannot be null

* defined in: [get-configuration output](get-configuration-output-properties-lets_encrypt.md "http://schema.nethserver.org/idp/get-configuration-output.json#/properties/lets_encrypt")

### lets_encrypt Type

`boolean`
