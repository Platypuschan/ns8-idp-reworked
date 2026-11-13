*** Settings ***
Library    SSHLibrary
Library    Collections
Library    String
Resource    idp.resource
Suite Setup    Skip without the module

*** Variables ***
${MARKER_REALM}    backup-marker

*** Keywords ***
Marker realm is managed
    ${rc} =    Execute Command    runagent -m ${module_id} python3 -c 'import sys, kcadmin; sys.exit(0 if "${MARKER_REALM}" in kcadmin.managed_realms(kcadmin.agent_client()) else 1)'
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0    Realm ${MARKER_REALM} is not served by the module

*** Test Cases ***
Create data that only the database holds
    ${rc} =    Execute Command    runagent -m ${module_id} python3 -c 'import kcadmin; kcadmin.agent_client().post("", {"realm": "${MARKER_REALM}", "enabled": True})'
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
    Marker realm is managed

Back up the module
    ${endpoint} =    Execute Command    api-cli run list-cluster-backup-endpoints | jq -r '.endpoints[0].url'
    Should Start With    ${endpoint}    webdav:
    ${payload} =    Evaluate    json.dumps({"name": "idp-ci", "provider": "cluster", "url": $endpoint, "password": "", "parameters": {}})    modules=json
    ${repository}    ${rc} =    Execute Command    api-cli run add-backup-repository --data '${payload}' | jq -r .id
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0    backup repository creation failed: ${repository}
    Set Suite Variable    ${repository}
    ${payload} =    Evaluate    json.dumps({"name": "idp-ci", "repository": $repository, "schedule": "daily", "retention": 1, "instances": [$module_id], "enabled": True})    modules=json
    ${backup_id}    ${rc} =    Execute Command    api-cli run add-backup --data '${payload}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0    backup creation failed: ${backup_id}
    ${output}    ${rc} =    Execute Command    api-cli run run-backup --data '{"id":${backup_id}}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0    backup failed: ${output}
    ${uuid} =    Execute Command    runagent -m ${module_id} printenv MODULE_UUID
    ${uuid} =    Strip String    ${uuid}
    Set Suite Variable    ${module_uuid}    ${uuid}
    # The dump was made by the module and is gone again after the run
    ${rc} =    Execute Command    runagent -m ${module_id} test ! -e idp.pg_dump
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0

Remove the module and restore it from the backup
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
    ${repositories} =    Run task    cluster/read-backup-repositories    {}
    ${path} =    Evaluate    [r['path'] for r in $repositories if r['uuid'] == $module_uuid and r['repository_id'] == $repository][0]
    ${payload} =    Evaluate    json.dumps({"repository": $repository, "path": $path, "snapshot": "", "node": 1})    modules=json
    ${output}    ${rc} =    Execute Command    api-cli run restore-module --data '${payload}'
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0    restore failed: ${output}
    ${restored} =    Evaluate    json.loads(r'''${output}''')['module_id']    modules=json
    Set Global Variable    ${module_id}    ${restored}

The restored module serves the restored data
    Retry test    Services are active
    Retry test    OIDC discovery is served through Traefik
    Wait Until Keyword Succeeds    120 seconds    5 seconds    Marker realm is managed

The restored module has its own admin credentials
    ${rc} =    Execute Command    runagent -m ${module_id} python3 -c 'import kcadmin; kcadmin.managed_realms(kcadmin.agent_client())'
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
    &{config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be Equal    ${config.host}    ${IDP_HOST}

Remove the marker realm
    ${rc} =    Execute Command    runagent -m ${module_id} python3 -c 'import kcadmin; kcadmin.agent_client().delete("/${MARKER_REALM}")'
    ...    return_rc=True    return_stdout=False
    Should Be Equal As Integers    ${rc}    0
