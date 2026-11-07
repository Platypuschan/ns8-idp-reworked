package org.nethserver.keycloak.access;

import java.util.List;
import org.keycloak.Config;
import org.keycloak.authentication.Authenticator;
import org.keycloak.authentication.AuthenticatorFactory;
import org.keycloak.models.AuthenticationExecutionModel.Requirement;
import org.keycloak.models.KeycloakSession;
import org.keycloak.models.KeycloakSessionFactory;
import org.keycloak.provider.ProviderConfigProperty;

public final class DeviceCertificateFactory implements AuthenticatorFactory {
    @Override public String getId() { return "ns8-device-certificate"; }
    @Override public String getDisplayType() { return "NS8 device certificate"; }
    @Override public String getReferenceCategory() { return "x509"; }
    @Override public String getHelpText() { return "Administrator-pinned certificates for existing LDAP users."; }
    @Override public boolean isConfigurable() { return false; }
    @Override public boolean isUserSetupAllowed() { return false; }
    @Override public Requirement[] getRequirementChoices() { return new Requirement[]{Requirement.ALTERNATIVE, Requirement.DISABLED}; }
    @Override public List<ProviderConfigProperty> getConfigProperties() { return List.of(); }
    @Override public Authenticator create(KeycloakSession session) { return new DeviceCertificate(); }
    @Override public void init(Config.Scope config) { }
    @Override public void postInit(KeycloakSessionFactory factory) { }
    @Override public void close() { }
}
