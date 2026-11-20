# add-realm input Schema

```txt
http://schema.nethserver.org/idp/add-realm-input.json
```

Create the realm of a user domain, before any client registers in it. The idp is bound to the user domain

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                              |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [add-realm-input.json](idp/add-realm-input.json "open original schema") |

## add-realm input Type

`object` ([add-realm input](add-realm-input.md))

## add-realm input Examples

```json
{
  "domain": "dp.example.org"
}
```

# add-realm input Properties

| Property          | Type     | Required | Nullable       | Defined by                                                                                                                         |
| :---------------- | :------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------- |
| [domain](#domain) | `string` | Required | cannot be null | [add-realm input](add-realm-input-properties-domain.md "http://schema.nethserver.org/idp/add-realm-input.json#/properties/domain") |

## domain

User domain, which is also the realm name

`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [add-realm input](add-realm-input-properties-domain.md "http://schema.nethserver.org/idp/add-realm-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**minimum length**: the minimum number of characters for this string is: `1`
