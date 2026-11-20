# get-client-access input Schema

```txt
http://schema.nethserver.org/idp/get-client-access-input.json
```

Read the access policy of a client. Modules read the policy of their own client; administrators pass client_id

| Abstract            | Extensible | Status         | Identifiable | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                              |
| :------------------ | :--------- | :------------- | :----------- | :---------------- | :-------------------- | :------------------ | :-------------------------------------------------------------------------------------- |
| Can be instantiated | No         | Unknown status | No           | Forbidden         | Forbidden             | none                | [get-client-access-input.json](idp/get-client-access-input.json "open original schema") |

## get-client-access input Type

`object` ([get-client-access input](get-client-access-input.md))

## get-client-access input Examples

```json
{
  "domain": "ad.example.org"
}
```

```json
{
  "domain": "ad.example.org",
  "client_id": "vaultwarden1",
  "live": true,
  "user": "alice"
}
```

# get-client-access input Properties

| Property                | Type      | Required | Nullable       | Defined by                                                                                                                                                       |
| :---------------------- | :-------- | :------- | :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [domain](#domain)       | `string`  | Required | cannot be null | [get-client-access input](get-client-access-input-properties-domain.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/domain")       |
| [client_id](#client_id) | `string`  | Optional | cannot be null | [get-client-access input](get-client-access-input-properties-client_id.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/client_id") |
| [live](#live)           | `boolean` | Optional | cannot be null | [get-client-access input](get-client-access-input-properties-live.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/live")           |
| [user](#user)           | `string`  | Optional | cannot be null | [get-client-access input](get-client-access-input-properties-user.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/user")           |

## domain



`domain`

* is required

* Type: `string`

* cannot be null

* defined in: [get-client-access input](get-client-access-input-properties-domain.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/domain")

### domain Type

`string`

### domain Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z0-9.-]+$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z0-9.-%5D%2B%24 "try regular expression with regexr.com")

## client_id

Administrators only: the client to read

`client_id`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-client-access input](get-client-access-input-properties-client_id.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/client_id")

### client_id Type

`string`

### client_id Constraints

**pattern**: the string must match the following regular expression:&#x20;

```regexp
^[a-zA-Z0-9_-]+$
```

[try pattern](https://regexr.com/?expression=%5E%5Ba-zA-Z0-9_-%5D%2B%24 "try regular expression with regexr.com")

## live

Also check that LDAP is reachable and the group exists in LDAP

`live`

* is optional

* Type: `boolean`

* cannot be null

* defined in: [get-client-access input](get-client-access-input-properties-live.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/live")

### live Type

`boolean`

## user

Administrators only, with live: check if this user can sign in to the client now

`user`

* is optional

* Type: `string`

* cannot be null

* defined in: [get-client-access input](get-client-access-input-properties-user.md "http://schema.nethserver.org/idp/get-client-access-input.json#/properties/user")

### user Type

`string`

### user Constraints

**minimum length**: the minimum number of characters for this string is: `1`
