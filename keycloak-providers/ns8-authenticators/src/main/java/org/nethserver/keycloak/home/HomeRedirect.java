package org.nethserver.keycloak.home;

import jakarta.ws.rs.GET;
import jakarta.ws.rs.Path;
import jakarta.ws.rs.core.CacheControl;
import jakarta.ws.rs.core.Response;
import java.net.URI;
import org.keycloak.Config;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.services.resource.RealmResourceProvider;
import org.keycloak.urls.UrlType;

/** Target of the ns8 welcome theme, the page of the host root. With
 * exactly one enabled realm besides master, redirect to its account
 * console, where the users of the user domain log in. Otherwise show
 * a neutral page: the Administration Console is reachable only from the
 * node, and a page listing the realms would publish the user domain names.
 */
public final class HomeRedirect implements RealmResourceProvider {
    private static final String NEUTRAL_PAGE = "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        + "<title>Single sign-on</title></head><body id=\"ns8-home\">"
        + "<p>Please sign in from the application you want to use.</p></body></html>";

    private final KeycloakSession session;

    HomeRedirect(KeycloakSession session) {
        this.session = session;
    }

    @Override
    public Object getResource() {
        return this;
    }

    @GET
    @Path("")
    public Response redirect() {
        var realms = session.realms().getRealmsStream()
            .filter(RealmModel::isEnabled)
            .map(RealmModel::getName)
            .filter(name -> !Config.getAdminRealm().equals(name))
            .limit(2)
            .toList();
        var noCache = new CacheControl();
        noCache.setNoCache(true);
        noCache.setNoStore(true);
        if (realms.size() != 1) {
            return Response.ok(NEUTRAL_PAGE, "text/html; charset=utf-8").cacheControl(noCache).build();
        }
        URI target = session.getContext().getUri(UrlType.FRONTEND).getBaseUriBuilder()
            .path("realms/{realm}/account/").build(realms.get(0));
        return Response.status(Response.Status.FOUND).location(target).cacheControl(noCache).build();
    }

    @Override
    public void close() { }
}
