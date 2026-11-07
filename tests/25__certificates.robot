*** Settings ***
Library    SSHLibrary
Library    Process
Resource    idp.resource
Suite Setup    Require disposable proxy test

*** Variables ***
${CERTIFICATE_TRANSPORT_TEST}    ${FALSE}
${CERTIFICATE_APP}    x509test1
${CERTIFICATE_REDIRECT}    https://certificate-app.fqdn.test/callback

*** Keywords ***
Require disposable proxy test
    Skip without the module
    Skip If    not $CERTIFICATE_TRANSPORT_TEST    Companion proxy fixture not requested

Certificate authorization
    [Arguments]    ${mode}    ${expected}
    ${output}    ${errors}    ${rc} =    Execute Command    python3 /tmp/ns8-x509-check.py ${IDP_HOST} ${USER_DOMAIN} ${CERTIFICATE_APP} ${CERTIFICATE_REDIRECT} ${mode}
    ...    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0    ${errors}
    &{result} =    Evaluate    json.loads($output)    modules=json
    Should Be Equal    ${result.code}    ${expected}
    RETURN    ${result}

*** Test Cases ***
Install the reviewed proxy capability only in the disposable guest
    ${result} =    Run Process    bash    -c    command -v patch >/dev/null || (apt-get update -qq && apt-get install -y -qq patch)
    Should Be Equal As Integers    ${result.rc}    0
    ${folder} =    Evaluate    tempfile.mkdtemp(prefix='ns8-x509-proxy-')    modules=tempfile
    ${result} =    Run Process    python3    ${CURDIR}/../integrations/ns8-traefik/prepare.py    ${folder}
    Should Be Equal As Integers    ${result.rc}    0    ${result.stderr}
    Put File    ${folder}/imageroot/actions/set-route/20writeconfig    /tmp/ns8-x509-proxy-writeconfig    mode=0644
    Put File    ${folder}/imageroot/actions/set-route/29waitsync    /tmp/ns8-x509-proxy-waitsync    mode=0644
    Put File    ${folder}/imageroot/pypkg/get_route.py    /tmp/ns8-x509-proxy-getroute    mode=0644
    Put File    ${folder}/imageroot/actions/set-route/validate-input.json    /tmp/ns8-x509-proxy-input    mode=0644
    Put File    ${folder}/imageroot/actions/get-route/validate-output.json    /tmp/ns8-x509-proxy-output    mode=0644
    Put File    ${CURDIR}/ns8/install-proxy-fixture.py    /tmp/ns8-x509-proxy-install.py    mode=0644
    ${output}    ${errors}    ${rc} =    Execute Command    runagent -m traefik1 python3 /tmp/ns8-x509-proxy-install.py
    ...    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0    ${errors}
    Put File    ${CURDIR}/ns8/check-certificate.py    /tmp/ns8-x509-check.py    mode=0644

Enroll the domain user and enable certificate login
    Execute Command    redis-cli --no-auth-warning hset cluster/module_domains ${CERTIFICATE_APP} ${USER_DOMAIN}
    Run task    module/${module_id}/register-client    {"domain": "${USER_DOMAIN}", "module_id": "${CERTIFICATE_APP}", "redirect_uris": ["${CERTIFICATE_REDIRECT}"]}    decode_json=${FALSE}
    Run task    module/${module_id}/alter-realm-client    {"domain": "${USER_DOMAIN}", "client_id": "${CERTIFICATE_APP}", "access_group": "g1"}    decode_json=${FALSE}
    ${certificate}    ${rc} =    Execute Command    umask 077 && openssl req -x509 -newkey rsa:2048 -nodes -keyout /tmp/ns8-x509-native.key -out /tmp/ns8-x509-native.crt -days 2 -subj '/CN=ns8-native-test' -addext 'basicConstraints=critical,CA:FALSE' -addext 'keyUsage=critical,digitalSignature' -addext 'extendedKeyUsage=clientAuth' 2>/dev/null && cat /tmp/ns8-x509-native.crt
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    ${request} =    Evaluate    json.dumps(dict(domain=$USER_DOMAIN, operation='enroll', username='u1', label='QEMU device', certificate=$certificate))    modules=json
    Run task    module/${module_id}/alter-certificates    ${request}    decode_json=${FALSE}
    Run task    module/${module_id}/alter-certificates    {"domain": "${USER_DOMAIN}", "operation": "enable"}    decode_json=${FALSE}
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Be True    ${state.enabled}
    Should Be True    ${state.operational}
    Set Suite Variable    ${DEVICE_FINGERPRINT}    ${state.certificates[0]['fingerprint']}
    Retry test    Certificate authorization    certificate    ${TRUE}

Missing and forged certificates cannot sign in
    &{state} =    Certificate authorization    none    ${FALSE}
    Should Be True    ${state.password_form}
    Certificate authorization    forged    ${FALSE}

A locked directory account cannot sign in with its certificate
    Run task    module/${ldap_module_id}/alter-user    {"user": "u1", "locked": true}    decode_json=${FALSE}
    Retry test    Certificate authorization    certificate    ${FALSE}
    Run task    module/${ldap_module_id}/alter-user    {"user": "u1", "locked": false}    decode_json=${FALSE}
    Retry test    Certificate authorization    certificate    ${TRUE}

Restart and reconfiguration preserve certificate login
    ${rc} =    Execute Command    runagent -m ${module_id} systemctl --user restart keycloak.service
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
    Retry test    Certificate authorization    certificate    ${TRUE}
    Run task    module/${module_id}/configure-module    {"host": "${IDP_HOST}", "lets_encrypt": false}    decode_json=${FALSE}
    Retry test    Certificate authorization    certificate    ${TRUE}
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Be True    ${state.operational}

Revoke and disable certificate login
    Run task    module/${module_id}/alter-certificates    {"domain": "${USER_DOMAIN}", "operation": "revoke", "fingerprint": "${DEVICE_FINGERPRINT}"}    decode_json=${FALSE}
    Certificate authorization    certificate    ${FALSE}
    Run task    module/${module_id}/alter-certificates    {"domain": "${USER_DOMAIN}", "operation": "disable"}    decode_json=${FALSE}
    &{state} =    Run task    module/${module_id}/get-certificates    {"domain": "${USER_DOMAIN}"}
    Should Not Be True    ${state.enabled}
    Should Be Empty    ${state.certificates}
    &{state} =    Certificate authorization    none    ${FALSE}
    Should Be True    ${state.password_form}
    Run task    module/${module_id}/remove-realm    {"domain": "${USER_DOMAIN}", "force": true}    decode_json=${FALSE}
    Execute Command    redis-cli --no-auth-warning hdel cluster/module_domains ${CERTIFICATE_APP}
