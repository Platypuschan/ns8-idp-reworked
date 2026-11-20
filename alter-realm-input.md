# alter-realm input Schema

```txt
http://schema.nethserver.org/idp/alter-realm-input.json
```

Change the settings of a realm

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                  |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [alter-realm-input.json](idp/alter-realm-input.json "open original schema") |

## alter-realm input Type

`object` ([alter-realm input](alter-realm-input.md))

## alter-realm input Examples

```json
{
  "domain": "dp.example.org",
  "enabled": false
}
```

# alter-realm input Properties

| Property            | Type      | Required | Nullable       | Defined by                                                                                                                                 |
| :------------------ | :-------- | :------- | :------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| [domain](#domain)   | `string`  | Required | cannot be null | [alter-realm input](alter-realm-input-properties-domain.md "http://schema.nethserver.org/idp/alter-realm-input.json#/properties/domain")   |
| [enabled](#enabled) | `boolean` | Optional | cannot be null | [alter-realm input](alter-realm-input-properties-enabled.md "http://schema.nethserver.org/idp/alter-realm-input.json#/properties/enabled") |

## domain

User domain, which is also the realm name

`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [alter-realm input](alter-realm-input-properties-domain.md "http://schema.nethserver.org/idp/alter-realm-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**minimum length**: the minimum number of characters for this string is: `1`

## enabled

A disabled realm refuses the logins of all its clients

`enabled`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [alter-realm input](alter-realm-input-properties-enabled.md "http://schema.nethserver.org/idp/alter-realm-input.json#/properties/enabled")

### enabled Type

`boolean`
