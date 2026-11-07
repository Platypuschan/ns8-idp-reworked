<template>
  <cv-grid fullWidth>
    <cv-row
      ><cv-column class="page-title"
        ><h2>{{ $t("certificates.title") }}</h2></cv-column
      ></cv-row
    >
    <cv-row
      ><cv-column>
        <p class="mg-bottom-lg">{{ $t("certificates.description") }}</p>
        <NsInlineNotification
          v-if="message"
          kind="error"
          :title="message"
          :showCloseButton="false"
        />
        <cv-tile light v-if="!realms.length && !loading.listRealms">{{
          $t("certificates.no_realms")
        }}</cv-tile>
        <cv-tile
          light
          v-for="realm in realms"
          :key="realm.name"
          class="mg-bottom-lg"
        >
          <h4>{{ realm.name }}</h4>
          <template v-if="states[realm.name]">
            <p>
              {{
                $t(
                  states[realm.name].enabled
                    ? "certificates.enabled"
                    : "certificates.disabled"
                )
              }}
            </p>
            <NsInlineNotification
              v-if="
                states[realm.name].enabled && !states[realm.name].operational
              "
              kind="warning"
              :title="$t('certificates.not_operational')"
              :showCloseButton="false"
            />
            <NsButton
              kind="secondary"
              :disabled="busyRealm"
              @click="
                change(realm, {
                  operation: states[realm.name].enabled ? 'disable' : 'enable',
                })
              "
            >
              {{
                $t(
                  states[realm.name].enabled
                    ? "certificates.disable"
                    : "certificates.enable"
                )
              }}
            </NsButton>
            <p class="mg-top-md">{{ $t("certificates.revoke_notice") }}</p>
            <ul>
              <li
                v-for="cert in states[realm.name].certificates"
                :key="cert.fingerprint"
                class="mg-bottom-md"
              >
                <strong>{{ cert.label }}</strong> — {{ cert.username }}<br />
                {{ $t("certificates.expires") }} {{ cert.not_after }}
                <strong v-if="certificateState(cert)">
                  ({{ $t("certificates." + certificateState(cert)) }})</strong
                ><br />
                <code class="fingerprint">{{ cert.fingerprint }}</code
                ><br />
                <NsButton
                  kind="danger--tertiary"
                  :disabled="busyRealm"
                  @click="revoke(realm, cert)"
                  >{{ $t("certificates.revoke") }}</NsButton
                >
              </li>
            </ul>
            <cv-form @submit.prevent="enroll(realm)">
              <cv-text-input
                :label="$t('certificates.username')"
                v-model="forms[realm.name].username"
                :disabled="busyRealm"
                required
              />
              <cv-text-input
                :label="$t('certificates.label')"
                v-model="forms[realm.name].label"
                :disabled="busyRealm"
                required
              />
              <label :for="'certificate-' + realm.name">{{
                $t("certificates.public_certificate")
              }}</label>
              <input
                :key="fileInputs[realm.name]"
                :id="'certificate-' + realm.name"
                type="file"
                accept=".crt,.pem,.cer"
                :disabled="busyRealm"
                @change="readCertificate(realm, $event)"
              />
              <NsButton
                kind="primary"
                :disabled="
                  busyRealm ||
                  !forms[realm.name].certificate ||
                  !forms[realm.name].username ||
                  !forms[realm.name].label
                "
                >{{ $t("certificates.enroll") }}</NsButton
              >
            </cv-form>
          </template>
        </cv-tile>
      </cv-column></cv-row
    >
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import Access from "./Access.vue";

export default {
  name: "Certificates",
  extends: Access,
  data() {
    return {
      q: { page: "certificates" },
      states: {},
      forms: {},
      fileInputs: {},
      message: "",
      busyRealm: false,
    };
  },
  pageTitle() {
    return this.$t("certificates.title") + " - " + this.appName;
  },
  methods: {
    async listRealms() {
      this.loading.listRealms = true;
      const [error, result] = await to(this.runTask("list-realms", {}));
      this.loading.listRealms = false;
      if (error) {
        this.message = this.errorText(error);
        return;
      }
      this.realms = result.realms;
      for (const realm of this.realms) {
        this.resetForm(realm);
        await this.load(realm);
      }
    },
    resetForm(realm) {
      this.$set(this.forms, realm.name, {
        username: "",
        label: "",
        certificate: "",
      });
      // A new key clears the file input, which has no bindable value
      this.$set(this.fileInputs, realm.name, Date.now());
    },
    certificateState(cert) {
      if (cert.revoked) return "revocation_pending";
      const remaining = new Date(cert.not_after) - new Date();
      if (remaining <= 0) return "expired";
      return remaining < 30 * 24 * 3600 * 1000 ? "expires_soon" : "";
    },
    async load(realm) {
      const [error, result] = await to(
        this.runTask("get-certificates", { domain: realm.name })
      );
      if (error) {
        this.message = this.errorText(error);
        return;
      }
      this.$set(this.states, realm.name, result);
    },
    errorText(error) {
      return Array.isArray(error)
        ? error
            .map((item) => this.$t("certificates.error_" + item.error))
            .join(" ")
        : String(error);
    },
    async readCertificate(realm, event) {
      const file = event.target.files[0];
      this.forms[realm.name].certificate = "";
      if (!file) return;
      if (file.size > 16384) {
        this.message = this.$t("certificates.error_invalid_certificate");
        return;
      }
      const text = await file.text();
      if (
        !/^\s*-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*$/.test(
          text
        )
      ) {
        this.message = this.$t("certificates.error_invalid_certificate");
        return;
      }
      this.forms[realm.name].certificate = text;
      this.message = "";
    },
    async change(realm, data) {
      if (
        data.operation === "enable" &&
        !window.confirm(this.$t("certificates.confirm_enable"))
      )
        return;
      this.busyRealm = true;
      this.message = "";
      const [error] = await to(
        this.runTask("alter-certificates", { domain: realm.name, ...data })
      );
      if (error) this.message = this.errorText(error);
      await this.load(realm);
      this.busyRealm = false;
      return !error;
    },
    async enroll(realm) {
      const enrolled = await this.change(realm, {
        operation: "enroll",
        ...this.forms[realm.name],
      });
      if (enrolled) this.resetForm(realm);
    },
    async revoke(realm, cert) {
      if (
        window.confirm(
          this.$t("certificates.confirm_revoke", { label: cert.label })
        )
      ) {
        await this.change(realm, {
          operation: "revoke",
          fingerprint: cert.fingerprint,
        });
      }
    },
  },
};
</script>

<style scoped>
.fingerprint {
  overflow-wrap: anywhere;
}
.cv-form .bx--form-item,
input[type="file"] {
  margin-bottom: 1rem;
}
</style>
