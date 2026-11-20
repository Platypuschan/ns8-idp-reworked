# list-realms output Schema

```txt
http://schema.nethserver.org/idp/list-realms-output.json
```

Realms of the idp, with the clients of NS8 modules

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                    |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [list-realms-output.json](idp/list-realms-output.json "open original schema") |

## list-realms output Type

`object` ([list-realms output](list-realms-output.md))

## list-realms output Examples

```json
{
  "realms": [
    {
      "name": "dp.example.org",
      "enabled": true,
      "issuer": "https://sso.example.org/realms/dp.example.org",
      "user_domain_found": true,
      "clients": [
        {
          "client_id": "nextcloud1",
          "enabled": true,
          "access_group": "services_nextcloud"
        }
      ]
    }
  ]
}
```

# list-realms output Properties

| Property          | Type    | Required | Nullable       | Defined by                                                                                                                                  |
| :---------------- | :------ | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| [realms](#realms) | `array` | Required | cannot be null | [list-realms output](list-realms-output-properties-realms.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms") |

## realms



`realms`

* is required

* Type: `object[]` ([Details](list-realms-output-properties-realms-items.md))

* cannot be null

* defined in: [list-realms output](list-realms-output-properties-realms.md "http://schema.nethserver.org/idp/list-realms-output.json#/properties/realms")

### realms Type

`object[]` ([Details](list-realms-output-properties-realms-items.md))
