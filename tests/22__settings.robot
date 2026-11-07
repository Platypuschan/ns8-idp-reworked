*** Settings ***
Library    SSHLibrary
Resource    idp.resource
Suite Setup    Skip without the module
Suite Teardown    Run Keyword And Ignore Error    Configure policies    true

*** Keywords ***
Configure policies
    [Arguments]    ${value}
    Run task    module/${module_id}/configure-module    {"host": "${IDP_HOST}", "lets_encrypt": false, "restrict_admin_console": ${value}, "directory_groups_only": ${value}, "account_home_redirect": ${value}, "strict_client_uris": ${value}}    decode_json=${FALSE}

Admin route
    ${route} =    Run task    module/traefik1/get-route    {"instance": "${module_id}-admin"}
    RETURN    ${route}

Host root redirect
    ${location} =    Execute Command    curl -sk -o /dev/null -w '\%{redirect_url}' --resolve ${IDP_HOST}:443:127.0.0.1 https://${IDP_HOST}/
    RETURN    ${location}

*** Test Cases ***
Site policies are on by default
    &{config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be True    ${config.restrict_admin_console}
    Should Be True    ${config.directory_groups_only}
    Should Be True    ${config.account_home_redirect}
    Should Be True    ${config.strict_client_uris}
    ${route} =    Admin route
    Should Not Be Empty    ${route}

Relaxed policies keep the upstream behavior
    Configure policies    false
    &{config} =    Run task    module/${module_id}/get-configuration    {}
    Should Not Be True    ${config.restrict_admin_console}
    Should Not Be True    ${config.account_home_redirect}
    ${route} =    Admin route
    Should Be Empty    ${route}
    ${location} =    Host root redirect
    Should End With    ${location}    /admin/

An omitted setting keeps its value
    Run task    module/${module_id}/configure-module    {"host": "${IDP_HOST}", "lets_encrypt": false}    decode_json=${FALSE}
    &{config} =    Run task    module/${module_id}/get-configuration    {}
    Should Not Be True    ${config.restrict_admin_console}

Policies can be restored
    Configure policies    true
    &{config} =    Run task    module/${module_id}/get-configuration    {}
    Should Be True    ${config.restrict_admin_console}
    ${route} =    Admin route
    Should Not Be Empty    ${route}
    ${page} =    Execute Command    curl -sk --resolve ${IDP_HOST}:443:127.0.0.1 https://${IDP_HOST}/
    Should Contain    ${page}    /realms/master/ns8-home
