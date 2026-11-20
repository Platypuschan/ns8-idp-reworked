package org.nethserver.keycloak.access;

import java.util.Arrays;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import jakarta.ws.rs.core.Response;
import org.keycloak.models.ClientSessionContext;
import org.keycloak.models.GroupModel;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.ProtocolMapperModel;
import org.keycloak.models.UserSessionModel;
import org.keycloak.protocol.oidc.mappers.AbstractOIDCProtocolMapper;
import org.keycloak.protocol.oidc.mappers.OIDCAccessTokenMapper;
import org.keycloak.protocol.oidc.mappers.OIDCIDTokenMapper;
import org.keycloak.protocol.oidc.mappers.UserInfoTokenMapper;
import org.keycloak.provider.ProviderConfigProperty;
import org.keycloak.representations.AccessToken;
import org.keycloak.representations.IDToken;
import org.keycloak.services.ErrorResponseException;

/** Deny token issuance, refresh and user info to users that are not current
 * members of the access group of the client: for example the redemption of
 * an authorization code issued before a group removal. Optionally it adds
 * one claim, by default "groups", with the current LDAP memberships of the
 * user in the listed groups only (config claim.groups, comma separated).
 */
public final class GroupTokenGate extends AbstractOIDCProtocolMapper
        implements OIDCAccessTokenMapper, OIDCIDTokenMapper, UserInfoTokenMapper {
    public static final String ID = "ns8-client-group-token-gate";
    @Override public String getId() { return ID; }
    @Override public String getDisplayType() { return "NS8 client access group at token issuance"; }
    @Override public String getDisplayCategory() { return TOKEN_MAPPER_CATEGORY; }
    @Override public String getHelpText() { return "Refuse token issuance when current LDAP group membership is absent"; }
    public static final String CLAIM_NAME = "claim.name";
    public static final String CLAIM_GROUPS = "claim.groups";
    @Override public List<ProviderConfigProperty> getConfigProperties() {
        return List.of(
            new ProviderConfigProperty(CLAIM_NAME, "Groups claim name", "Name of the claim, default groups",
                ProviderConfigProperty.STRING_TYPE, "groups"),
            new ProviderConfigProperty(CLAIM_GROUPS, "Groups in the claim",
                "Comma separated LDAP group names; only current memberships in these groups are added",
                ProviderConfigProperty.STRING_TYPE, ""));
    }
    private void addGroups(IDToken token, ProtocolMapperModel model, KeycloakSession session, UserSessionModel userSession) {
        var wanted = model.getConfig() == null ? null : model.getConfig().get(CLAIM_GROUPS);
        if (wanted == null || wanted.isBlank()) {
            return;
        }
        var name = model.getConfig().get(CLAIM_NAME);
        if (name == null || name.isBlank()) {
            name = "groups";
        }
        Set<String> names = Arrays.stream(wanted.split(",")).map(String::trim).filter(x -> !x.isEmpty())
            .collect(Collectors.toSet());
        var realm = session.getContext().getRealm();
        var live = GroupAccess.liveUser(session, realm, userSession.getUser());
        // Without a LDAP-only membership read the claim is empty, never stale
        List<String> groups = live == null ? List.of() : live.getGroupsStream().map(GroupModel::getName)
            .filter(names::contains).sorted().collect(Collectors.toList());
        token.getOtherClaims().put(name, groups);
    }
    private void check(KeycloakSession session, UserSessionModel userSession, ClientSessionContext ctx) {
        if (!GroupAccess.allowed(session, session.getContext().getRealm(), ctx.getClientSession().getClient(), userSession.getUser())) {
            throw new ErrorResponseException("access_denied", "Required client group membership is absent", Response.Status.FORBIDDEN);
        }
    }
    @Override public AccessToken transformAccessToken(AccessToken token, ProtocolMapperModel model,
            KeycloakSession session, UserSessionModel userSession, ClientSessionContext ctx) {
        check(session, userSession, ctx);
        addGroups(token, model, session, userSession);
        return token;
    }
    @Override public IDToken transformIDToken(IDToken token, ProtocolMapperModel model,
            KeycloakSession session, UserSessionModel userSession, ClientSessionContext ctx) {
        check(session, userSession, ctx);
        addGroups(token, model, session, userSession);
        return token;
    }
    @Override public AccessToken transformUserInfoToken(AccessToken token, ProtocolMapperModel model,
            KeycloakSession session, UserSessionModel userSession, ClientSessionContext ctx) {
        check(session, userSession, ctx);
        addGroups(token, model, session, userSession);
        return token;
    }
}
