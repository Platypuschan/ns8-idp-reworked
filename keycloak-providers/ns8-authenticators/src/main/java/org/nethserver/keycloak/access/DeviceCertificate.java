package org.nethserver.keycloak.access;

import java.security.MessageDigest;
import java.security.cert.X509Certificate;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.AuthenticationFlowError;
import org.keycloak.authentication.Authenticator;
import org.keycloak.component.ComponentModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.RealmModel;
import org.keycloak.models.UserModel;
import org.keycloak.models.cache.UserCache;
import org.keycloak.models.utils.StorageUnavailableUserModelDelegate;
import org.keycloak.protocol.oidc.OIDCLoginProtocol;
import org.keycloak.services.managers.AuthenticationManager;
import org.keycloak.services.x509.X509ClientCertificateLookup;
import org.keycloak.util.JsonSerialization;
import org.keycloak.util.TokenUtil;

/** Exact certificate pins owned by administrators, never user profile fields.
 * TLS proves key possession at Traefik; its strip/pass middleware prevents
 * attacker-supplied certificate headers. No trust in a certificate's name/CA.
 */
public final class DeviceCertificate implements Authenticator {
    private static final String LDAP_MAPPER_TYPE = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper";
    private static final String ACCOUNT_MAPPER = "ns8-account-state";
    private static final String ACCOUNT_ATTRIBUTE = "ns8.account_state";
    private static final long FILETIME_EPOCH_OFFSET_MILLIS = 11_644_473_600_000L;

    @Override public void authenticate(AuthenticationFlowContext context) {
        if (!"true".equals(context.getRealm().getAttribute("ns8.x509.enabled"))) {
            context.attempted();
            return;
        }
        // prompt=login and an expired max_age ask the person to authenticate
        // again, which unattended device possession cannot answer. This also
        // keeps a way to sign in with another account on an enrolled device.
        var authSession = context.getAuthenticationSession();
        if (authSession.getAuthNote(AuthenticationManager.FORCED_REAUTHENTICATION) != null
                || TokenUtil.hasPrompt(authSession.getClientNote(OIDCLoginProtocol.PROMPT_PARAM),
                    OIDCLoginProtocol.PROMPT_VALUE_LOGIN)) {
            context.attempted();
            return;
        }
        String expectedProof = context.getRealm().getAttribute("ns8.x509.proxy_secret");
        String actualProof = context.getHttpRequest().getHttpHeaders().getHeaderString("X-NS8-X509-Proxy");
        if (expectedProof == null || actualProof == null || !MessageDigest.isEqual(
                expectedProof.getBytes(StandardCharsets.UTF_8), actualProof.getBytes(StandardCharsets.UTF_8))) {
            context.attempted();
            return;
        }
        // Avoid invoking the lookup (which logs a warning) for normal logins.
        if (context.getHttpRequest().getHttpHeaders().getHeaderString("X-Forwarded-Tls-Client-Cert") == null) {
            context.attempted();
            return;
        }
        try {
            X509ClientCertificateLookup lookup = context.getSession().getProvider(X509ClientCertificateLookup.class);
            X509Certificate[] chain = lookup.getCertificateChain(context.getHttpRequest());
            if (chain == null || chain.length == 0) {
                context.attempted();
                return;
            }
            X509Certificate cert = chain[0];
            cert.checkValidity();
            if (cert.getBasicConstraints() >= 0) throw new IllegalArgumentException("CA certificate");
            boolean[] usage = cert.getKeyUsage();
            if (usage != null && !usage[0]) throw new IllegalArgumentException("Signing disabled");
            if (cert.getExtendedKeyUsage() == null || !cert.getExtendedKeyUsage().contains("1.3.6.1.5.5.7.3.2"))
                throw new IllegalArgumentException("Client authentication EKU required");
            String fingerprint = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(cert.getEncoded()));
            String record = context.getRealm().getAttribute("ns8.x509.device." + fingerprint);
            if (record == null) {
                context.attempted();
                return;
            }
            Map<?, ?> pin = JsonSerialization.readValue(record, Map.class);
            if (Boolean.TRUE.equals(pin.get("revoked"))) {
                context.attempted();
                return;
            }
            KeycloakSession session = context.getSession();
            RealmModel realm = context.getRealm();
            String userId = (String) pin.get("user_id");
            UserModel user = session.users().getUserById(realm, userId);
            UserCache cache = session.getProvider(UserCache.class);
            if (cache != null && user != null) cache.evict(realm, user);
            user = session.users().getUserById(realm, userId);
            if (user == null || user instanceof StorageUnavailableUserModelDelegate || !user.isEnabled()
                    || user.getFederationLink() == null
                    || !pin.get("ldap_id").equals(user.getFirstAttribute("LDAP_ID"))
                    || !activeInDirectory(realm, user))
                throw new IllegalArgumentException("Directory identity unavailable");
            context.setUser(user);
            context.getEvent().detail("auth_method", "ns8-device-certificate");
            context.getEvent().detail("ns8_certificate_sha256", fingerprint);
            context.success();
        } catch (Exception exception) {
            // Invalid certificates/directory failures never become successful
            // certificate authentication. Password fallback stays available.
            context.failure(AuthenticationFlowError.INVALID_CREDENTIALS);
        }
    }
    /** Certificate sign-in has no LDAP bind, which rejects these accounts for
     * passwords. Any lock value counts. Without a live value the state is
     * unknown, and an unknown state must never read as "not locked". */
    private static boolean activeInDirectory(RealmModel realm, UserModel user) {
        ComponentModel federation = realm.getComponent(user.getFederationLink());
        if (federation == null) return false;
        boolean activeDirectory = "ad".equals(federation.getConfig().getFirst("vendor"));
        String attribute = activeDirectory ? "accountExpires" : "pwdAccountLockedTime";
        boolean live = realm.getComponentsStream(federation.getId(), LDAP_MAPPER_TYPE)
            .anyMatch(m -> ACCOUNT_MAPPER.equals(m.getName())
                && attribute.equals(m.getConfig().getFirst("ldap.attribute"))
                && ACCOUNT_ATTRIBUTE.equals(m.getConfig().getFirst("user.model.attribute"))
                && "true".equals(m.getConfig().getFirst("always.read.value.from.ldap")));
        if (!live) return false;
        String value = user.getFirstAttribute(ACCOUNT_ATTRIBUTE);
        if (value == null || value.isEmpty()) return true;
        if (!activeDirectory) return false;
        // FILETIME: 100 ns ticks since 1601. 0 and Long.MAX_VALUE mean never.
        long ticks = Long.parseLong(value);
        return ticks == 0 || ticks == Long.MAX_VALUE
            || Instant.ofEpochMilli(ticks / 10_000 - FILETIME_EPOCH_OFFSET_MILLIS).isAfter(Instant.now());
    }

    @Override public void action(AuthenticationFlowContext context) { authenticate(context); }
    @Override public boolean requiresUser() { return false; }
    @Override public boolean configuredFor(KeycloakSession session, RealmModel realm, UserModel user) { return true; }
    @Override public void setRequiredActions(KeycloakSession session, RealmModel realm, UserModel user) { }
    @Override public void close() { }
}
