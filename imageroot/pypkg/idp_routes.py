"""Keep the internal Keycloak admin API off the public host route."""
import os
import copy
import sys
import time
import agent
import agent.tasks
import idpcert
import idpsettings

def restrict_admin(host, lets_encrypt=False):
    agent.set_route({
        'instance': os.environ['MODULE_ID'] + '-admin',
        'url': 'http://127.0.0.1:' + os.environ['TCP_PORT'],
        'host': host, 'path': '/admin', 'ip_allowlist': ['127.0.0.1/32', '::1/128'],
        'http2https': True, 'lets_encrypt': lets_encrypt,
    })


def remove_admin_route():
    """Drop the restriction: the host route then also serves /admin."""
    instance = os.environ['MODULE_ID'] + '-admin'
    traefik = agent.resolve_agent_id('traefik@node')
    if traefik and agent.get_route(instance):
        response = agent.tasks.run(agent_id=traefik, action='delete-route',
                                   data={'instance': instance},
                                   extra={'isNotificationHidden': True})
        agent.assert_exp(response['exit_code'] == 0, 'Unable to remove admin route')


def _write_routes(routes):
    """Write all routes of the hostname one after the other, report success.

    agent.set_route() would exit on errors and skip the rollback. Parallel
    tasks are unsafe: set-route truncates its file while another task parses
    every file in configs/. The patched 29waitsync skips its wait, because
    Traefik drops the routers of a hostname while their TLS options differ.
    The acme checks are off: these routes keep the certificate they have, and
    configure-module already validated new ones.
    """
    success = True
    for route in routes:
        response = agent.set_route({**route, 'lets_encrypt_check': False, 'lets_encrypt_cleanup': False},
                                   error_passthrough=False)
        if response['exit_code'] != 0:
            print(f"set-route {route['instance']} failed: {response.get('error')}", file=sys.stderr)
            success = False
    return success


def _in_sync(routes, proof, host, lets_encrypt):
    """True if the proxy already serves the wanted certificate transport."""
    return all(route.get('client_certificates') is True and route.get('host') == host
               and route.get('headers', {}).get('request', {}).get(idpcert.PROOF_HEADER) == proof
               and (lets_encrypt is None or route.get('lets_encrypt') == lets_encrypt)
               for route in routes)


def certificate_transport(value, host=None, lets_encrypt=None, admin_route=None):
    """Require an acknowledged Traefik capability, never trust ignored input.

    Both routers for the hostname must use the same TLS options; otherwise
    Traefik falls back to default options because TLS precedes path routing.
    """
    host = host or os.environ['IDP_HOSTNAME']
    if admin_route is None:
        admin_route = idpsettings.get('restrict_admin_console')
    original = [(os.environ['MODULE_ID'] + suffix,
                 agent.get_route(os.environ['MODULE_ID'] + suffix))
                for suffix in (('', '-admin') if admin_route else ('',))]
    if lets_encrypt is None and not all(old for _, old in original):
        # The route is the only record of the Let's Encrypt choice: guessing
        # it would silently switch the hostname to the default certificate.
        raise idpcert.CertificateError('idp_route_missing')
    proof = idpcert.proxy_secret() if value else ''
    if value and _in_sync([old for _, old in original], proof, host, lets_encrypt):
        return
    routes = []
    for index, (instance, old) in enumerate(original):
        route = copy.deepcopy(old)
        route.update(instance=instance, host=host,
                     url='http://127.0.0.1:' + os.environ['TCP_PORT'],
                     http2https=True, client_certificates=value)
        if lets_encrypt is not None:
            route['lets_encrypt'] = lets_encrypt
        if index:
            route.update(path='/admin', ip_allowlist=['127.0.0.1/32', '::1/128'])
        headers = route.setdefault('headers', {}).setdefault('request', {})
        headers[idpcert.HEADER] = ''
        headers['X-Forwarded-Tls-Client-Cert-Info'] = ''
        headers[idpcert.PROOF_HEADER] = proof
        routes.append(route)
    try:
        if not _write_routes(routes):
            raise idpcert.CertificateError('traefik_route_failed')
        if value:
            # Check the effective capability of both routes together.
            deadline = time.monotonic() + 20
            while not all(agent.get_route(route['instance']).get('client_certificates') is True
                          for route in routes):
                if time.monotonic() >= deadline:
                    raise idpcert.CertificateError('traefik_certificate_support_required')
                time.sleep(.2)
    except Exception:
        rollback = [{**old, 'instance': instance, 'headers': old.get('headers', {}),
                     'client_certificates': old.get('client_certificates', False)}
                    for instance, old in original if old]
        if rollback and not _write_routes(rollback):
            print('Cannot restore the previous IdP routes', file=sys.stderr)
        raise
