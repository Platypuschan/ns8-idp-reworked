*** Settings ***
Library    SSHLibrary
Library    Collections
Resource    idp.resource
Suite Setup    Skip without the module

*** Variables ***
${REDIRECT_URI}    https://app.fqdn.test/oidc/callback
# A module bound to the user domain, simulated with a binding record:
# the cluster bind-user-domains action binds only the calling module
${FAKE_APP}    fakeapp1

*** Keywords ***
Bind the fake application
    Execute Command    redis-cli --no-auth-warning hset cluster/module_domains ${FAKE_APP} ${USER_DOMAIN}

Unbind the fake application
    Execute Command    redis-cli --no-auth-warning hdel cluster/module_domains ${FAKE_APP}

Realm is absent
    [Arguments]    ${name}
    @{realms} =    List realms
    FOR    ${realm}    IN    @{realms}
        Should Not Be Equal    ${realm['name']}    ${name}
    END

Domain is bound
    [Arguments]    ${mid}    ${domain}
    ${domains} =    Bound domains    ${mid}
    Should Be True    $domain in $domains.split()

Domain is not bound
    [Arguments]    ${mid}    ${domain}
    ${domains} =    Bound domains    ${mid}
    Should Be True    $domain not in $domains.split()

Realm
    [Arguments]    ${name}
    @{realms} =    List realms
    FOR    ${realm}    IN    @{realms}
        IF    $realm['name'] == $name    RETURN    ${realm}
    END
    Fail    Realm ${name} not found

Client
    [Arguments]    ${realm_name}    ${client_id}
    &{realm} =    Realm    ${realm_name}
    FOR    ${client}    IN    @{realm.clients}
        IF    $client['client_id'] == $client_id    RETURN    ${client}
    END
    Fail    Client ${client_id} not found in realm ${realm_name}

Register client
    [Arguments]    ${client_id}    &{extra}
    &{input} =    Create Dictionary    domain=${USER_DOMAIN}    module_id=${client_id}    &{extra}
    ${json} =    Evaluate    json.dumps($input)    modules=json
    &{response} =    Run task    module/${module_id}/register-client    ${json}
    RETURN    ${response}

*** Test Cases ***
Create the user domain
    ${response} =    Run task    cluster/add-internal-provider    {"image": "openldap", "node": 1}
    Set Global Variable    ${ldap_module_id}    ${response['module_id']}
    Run task    module/${ldap_module_id}/configure-module    {"domain": "${USER_DOMAIN}", "admuser": "admin", "admpass": "Nethesis,1234", "provision": "new-domain"}
    Run task    module/${ldap_module_id}/add-user    {"user": "u1", "display_name": "First User", "password": "Nethesis,1234", "mail": "u1@fqdn.test"}
    Run task    module/${ldap_module_id}/add-group    {"group": "g1", "description": "Group One", "users": ["u1"]}

No realm before the first registration
    Realm is absent    ${USER_DOMAIN}

The host root shows a neutral page without realms
    ${location} =    Host root target
    Should Be Empty    ${location}
    ${page} =    Execute Command    curl -sk --resolve ${IDP_HOST}:443:127.0.0.1 https://${IDP_HOST}/realms/master/ns8-home
    Should Contain    ${page}    id="ns8-home"

The client owner is required
    &{error} =    Run validation    module/${module_id}/register-client    {"domain": "${USER_DOMAIN}"}
    Should Be Equal    ${error.error}    module_id_required

The client owner must be bound to the user domain
    &{error} =    Run validation    module/${module_id}/register-client    {"domain": "${USER_DOMAIN}", "module_id": "${FAKE_APP}"}
    Should Be Equal    ${error.error}    domain_not_bound_to_module

Register a client creates the realm
    Bind the fake application
    &{response} =    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    Should Be Equal    ${response.client_id}    ${FAKE_APP}
    Should Be Equal    ${response.realm}    ${USER_DOMAIN}
    Should Not Be Empty    ${response.client_secret}
    # The issuer is the one advertised by service discovery
    ${prefix} =    Execute Command    redis-cli --no-auth-warning hget module/${module_id}/srv/http/oidc issuer_url_prefix
    Should Be Equal    ${response.issuer}    ${prefix}${USER_DOMAIN}
    # The idp is bound to the user domain of its realm
    Domain is bound    ${module_id}    ${USER_DOMAIN}
    &{realm} =    Realm    ${USER_DOMAIN}
    Should Be True    ${realm.enabled}
    Should Be True    ${realm.user_domain_found}

The host root leads to the account console of the realm
    ${location} =    Host root target
    Should Be Equal    ${location}    https://${IDP_HOST}/realms/${USER_DOMAIN}/account/

The federation imports users and groups
    &{result} =    Run kccheck    sync    ${USER_DOMAIN}
    Should Start With    ${result.connection_url}    ldap://cluster-localnode:
    List Should Contain Value    ${result.users}    u1
    List Should Contain Value    ${result.groups}    g1
    # Hidden groups of the user domain are not imported
    List Should Not Contain Value    ${result.groups}    locals

The token carries the LDAP account key
    &{claims} =    Run kccheck    claims    ${USER_DOMAIN}    ${FAKE_APP}    u1
    Should Be Equal    ${claims.preferred_username}    u1
    Should Be Equal    ${claims.ldap_uuid}    ${claims.LDAP_ID}
    Set Suite Variable    ${u1_ldap_uuid}    ${claims.ldap_uuid}

A user logs in with the LDAP password
    &{result} =    Run kccheck    login    ${USER_DOMAIN}    ${FAKE_APP}    u1    Nethesis,1234
    Should Be Equal As Integers    ${result.status}    200
    Should Be Equal    ${result.claims['ldap_uuid']}    ${u1_ldap_uuid}
    &{result} =    Run kccheck    login    ${USER_DOMAIN}    ${FAKE_APP}    u1    WrongPassword,1234
    Should Be Equal As Integers    ${result.status}    400
    Should Be Equal    ${result.error}    invalid_grant

Register again returns the same secret
    &{first} =    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    &{second} =    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    Should Be Equal    ${first.client_secret}    ${second.client_secret}
    Set Suite Variable    ${old_secret}    ${first.client_secret}

Rotate the client secret
    &{rotated} =    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}    rotate_secret=${TRUE}
    Should Not Be Equal    ${rotated.client_secret}    ${old_secret}
    &{next} =    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    Should Be Equal    ${next.client_secret}    ${rotated.client_secret}

Add a client to the token audience
    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}    audience=@{{ ["broker"] }}
    &{claims} =    Run kccheck    claims    ${USER_DOMAIN}    ${FAKE_APP}    u1
    List Should Contain Value    ${claims.aud}    broker

Disable a client
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "enabled": false}    decode_json=${FALSE}
    &{client} =    Client    ${USER_DOMAIN}    ${FAKE_APP}
    Should Not Be True    ${client.enabled}
    ${status} =    Login page status    ${USER_DOMAIN}    ${FAKE_APP}    ${REDIRECT_URI}
    Should Be Equal    ${status}    400
    # Registering again does not enable the client
    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    &{client} =    Client    ${USER_DOMAIN}    ${FAKE_APP}
    Should Not Be True    ${client.enabled}

Enable a client
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "enabled": true}    decode_json=${FALSE}
    ${status} =    Login page status    ${USER_DOMAIN}    ${FAKE_APP}    ${REDIRECT_URI}
    Should Be Equal    ${status}    200

Alter a missing client
    &{error} =    Run validation    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "nosuchapp1", "enabled": false}
    Should Be Equal    ${error.error}    client_not_found

Restrict a client to a group
    Run task    module/${ldap_module_id}/add-group    {"group": "g2", "description": "Group Two", "users": []}    decode_json=${FALSE}
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "access_group": "g1"}    decode_json=${FALSE}
    &{client} =    Client    ${USER_DOMAIN}    ${FAKE_APP}
    Should Be Equal    ${client.access_group}    g1
    Should Be True    ${client.enabled}
    &{state} =    Run task    module/${module_id}/get-client-access    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "live": true, "user": "u1"}
    Should Be True    ${state.enforced}
    Should Be True    ${state.live['ok']}
    Should Be True    ${state.live['ldap_connection']}
    Should Be True    ${state.live['group_in_ldap']}
    Should Be True    ${state.live['user_allowed']}
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "access_group": "g2"}    decode_json=${FALSE}
    &{state} =    Run task    module/${module_id}/get-client-access    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "live": true, "user": "u1"}
    Should Be True    ${state.live['ok']}
    Should Not Be True    ${state.live['user_allowed']}
    &{error} =    Run validation    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "access_group": "nosuchgroup"}
    Should Be Equal    ${error.error}    group_not_found
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${FAKE_APP}", "access_group": null}    decode_json=${FALSE}
    &{client} =    Client    ${USER_DOMAIN}    ${FAKE_APP}
    Should Be Equal    ${client.access_group}    ${NONE}
    [Teardown]    Run task    module/${ldap_module_id}/remove-group    {"group": "g2"}    decode_json=${FALSE}

Certificate transport cannot silently enable with the stock proxy
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Not Be True    ${state.enabled}
    Should Be Empty    ${state.certificates}
    &{error} =    Run validation    module/${module_id}/alter-certificates    {"domain": "${USER_DOMAIN}", "operation": "enable"}
    Should Be Equal    ${error.error}    traefik_certificate_support_required
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Not Be True    ${state.enabled}
    ${status} =    Login page status    ${USER_DOMAIN}    ${FAKE_APP}    ${REDIRECT_URI}
    Should Be Equal    ${status}    200

Enroll and revoke a public device certificate
    ${certificate}    ${rc} =    Execute Command    umask 077 && openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/idp-x509-test.key -out /tmp/idp-x509-test.crt -days 2 -subj '/CN=ns8-test' -addext 'basicConstraints=critical,CA:FALSE' -addext 'keyUsage=critical,digitalSignature' -addext 'extendedKeyUsage=clientAuth' 2>/dev/null && cat /tmp/idp-x509-test.crt
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    ${request} =    Evaluate    json.dumps(dict(domain=$USER_DOMAIN, operation='enroll', username='u1', label='NS8 test', certificate=$certificate))    modules=json
    Run task    module/${module_id}/alter-certificates    ${request}    decode_json=${FALSE}
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Length Should Be    ${state.certificates}    1
    ${fingerprint} =    Set Variable    ${state.certificates[0]['fingerprint']}
    Should Be Equal    ${state.certificates[0]['username']}    u1
    Run task    module/${module_id}/alter-certificates    {"domain": "${USER_DOMAIN}", "operation": "revoke", "fingerprint": "${fingerprint}"}    decode_json=${FALSE}
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Be Empty    ${state.certificates}

Disable and enable the realm
    Run task    module/${module_id}/alter-realm    {"domain": "${USER_DOMAIN}", "enabled": false}    decode_json=${FALSE}
    &{realm} =    Realm    ${USER_DOMAIN}
    Should Not Be True    ${realm.enabled}
    ${status} =    Login page status    ${USER_DOMAIN}    ${FAKE_APP}    ${REDIRECT_URI}
    Should Be Equal    ${status}    400
    Run task    module/${module_id}/alter-realm    {"domain": "${USER_DOMAIN}", "enabled": true}    decode_json=${FALSE}
    ${status} =    Login page status    ${USER_DOMAIN}    ${FAKE_APP}    ${REDIRECT_URI}
    Should Be Equal    ${status}    200

Alter a missing realm
    &{error} =    Run validation    module/${module_id}/alter-realm    {"domain": "nosuch.test", "enabled": false}
    Should Be Equal    ${error.error}    realm_not_found

Add an existing realm
    &{error} =    Run validation    module/${module_id}/add-realm    {"domain": "${USER_DOMAIN}"}
    Should Be Equal    ${error.error}    realm_already_exists

Add the realm of a missing user domain
    &{error} =    Run validation    module/${module_id}/add-realm    {"domain": "nosuch.test"}
    Should Be Equal    ${error.error}    domain_not_found

A client is deleted when its module is unbound
    Unbind the fake application
    ${rc} =    Execute Command    runagent -m ${module_id} keycloak-post-start
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
    &{realm} =    Realm    ${USER_DOMAIN}
    Should Be Empty    ${realm.clients}

Remove a realm with clients only with force
    Bind the fake application
    Register client    ${FAKE_APP}    redirect_uris=@{{ ["${REDIRECT_URI}"] }}
    &{error} =    Run validation    module/${module_id}/remove-realm    {"domain": "${USER_DOMAIN}"}
    Should Be Equal    ${error.error}    realm_has_clients
    Run task    module/${module_id}/remove-realm    {"domain": "${USER_DOMAIN}", "force": true}    decode_json=${FALSE}
    Realm is absent    ${USER_DOMAIN}
    # The idp is unbound from the user domain
    Domain is not bound    ${module_id}    ${USER_DOMAIN}

Add a realm before any client
    &{response} =    Run task    module/${module_id}/add-realm    {"domain": "${USER_DOMAIN}"}
    Should Be Equal    ${response.name}    ${USER_DOMAIN}
    &{realm} =    Realm    ${USER_DOMAIN}
    Should Be Empty    ${realm.clients}
    Domain is bound    ${module_id}    ${USER_DOMAIN}
    &{result} =    Run kccheck    sync    ${USER_DOMAIN}
    List Should Contain Value    ${result.users}    u1

Remove an empty realm
    Unbind the fake application
    Run task    module/${module_id}/remove-realm    {"domain": "${USER_DOMAIN}"}    decode_json=${FALSE}
    Realm is absent    ${USER_DOMAIN}
