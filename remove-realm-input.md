# remove-realm input Schema

```txt
http://schema.nethserver.org/idp/remove-realm-input.json
```

Remove a realm and unbind the idp from its user domain. The clients of the realm are removed too: modules must register them again

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                    |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :---------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Allowed               | none                | [remove-realm-input.json](idp/remove-realm-input.json "open original schema") |

## remove-realm input Type

`object` ([remove-realm input](remove-realm-input.md))

## remove-realm input Examples

```json
{
  "domain": "dp.example.org",
  "force": true
}
```

# remove-realm input Properties

| Property          | Type      | Required | Nullable       | Defined by                                                                                                                                  |
| :---------------- | :-------- | :------- | :------------- | :------------------------------------------------------------------------------------------------------------------------------------------ |
| [domain](#domain) | `string`  | Required | cannot be null | [remove-realm input](remove-realm-input-properties-domain.md "http://schema.nethserver.org/idp/remove-realm-input.json#/properties/domain") |
| [force](#force)   | `boolean` | Optional | cannot be null | [remove-realm input](remove-realm-input-properties-force.md "http://schema.nethserver.org/idp/remove-realm-input.json#/properties/force")   |

## domain

User domain, which is also the realm name

`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [remove-realm input](remove-realm-input-properties-domain.md "http://schema.nethserver.org/idp/remove-realm-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**minimum length**: the minimum number of characters for this string is: `1`

## force

Remove the realm even if it has clients of NS8 modules

`force`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [remove-realm input](remove-realm-input-properties-force.md "http://schema.nethserver.org/idp/remove-realm-input.json#/properties/force")

### force Type

`boolean`

### force Default Value

The default value is:

```json
false
```
