# Untitled array in register-client input Schema

```txt
http://schema.nethserver.org/idp/register-client-input.json#/properties/post_logout_redirect_uris
```

URIs where the logout redirects the user. Applications should pass their exact logout URI. If the attribute is missing, a wildcard URI for each origin of the redirect URIs is set, like <https://cloud.example.org/>\*; an empty list allows none

| Abstract            | Extensible | Status         | Identifiable            | Custom Properties | Additional Properties | Access Restrictions | Defined In                                                                            |
| :------------------ | :--------- | :------------- | :---------------------- | :---------------- | :-------------------- | :------------------ | :------------------------------------------------------------------------------------ |
| Can be instantiated | No         | Unknown status | Unknown identifiability | Forbidden         | Allowed               | none                | [register-client-input.json\*](idp/register-client-input.json "open original schema") |

## post_logout_redirect_uris Type

`string[]`
