package org.nethserver.x509test;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.security.KeyChain;
import android.util.Base64;
import android.util.Log;
import android.webkit.ClientCertRequest;
import android.webkit.SslErrorHandler;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.json.JSONObject;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.security.KeyStore;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

/** Disposable physical-device OIDC/PKCE test app. No production settings,
 * user accounts or global server CA changes. The APK embeds only a short-lived
 * isolated fixture identity, and must never be uploaded as a CI artifact.
 */
public final class MainActivity extends Activity {
    JSONObject config;
    String verifier, state;
    TextView status;
    LinearLayout layout;
    X509Certificate server;
    final String redirect = "org.nethserver.x509test:/callback";
    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        try {
            config = new JSONObject(new String(getAssets().open("config.json").readAllBytes(), StandardCharsets.UTF_8));
            server = (X509Certificate) CertificateFactory.getInstance("X.509").generateCertificate(getAssets().open("server.crt"));
            layout = new LinearLayout(this);
            layout.setOrientation(LinearLayout.VERTICAL);
            layout.setPadding(20, 20, 20, 20);
            status = new TextView(this);
            status.setText("Isolated NS8 certificate / OIDC test. PKCS12 password: ns8-test");
            layout.addView(status);
            add("Install test certificate", () -> {
                try {
                    Intent install = KeyChain.createInstallIntent();
                    install.putExtra(KeyChain.EXTRA_PKCS12, getAssets().open("identity.p12").readAllBytes());
                    install.putExtra(KeyChain.EXTRA_NAME, "NS8 isolated L8 test");
                    startActivityForResult(install, 1);
                } catch (Exception e) { show("INSTALL FAILED: " + e.getClass().getSimpleName()); }
            });
            add("OIDC in Chrome", () -> login(false, false));
            add("OIDC in Chrome Custom Tab", () -> login(true, false));
            add("OIDC in WebView with KeyChain", () -> login(false, true));
            setContentView(layout);
        } catch (Exception e) { throw new IllegalStateException(e); }
    }
    void add(String title, Runnable action) {
        Button button = new Button(this);
        button.setText(title);
        button.setOnClickListener(v -> action.run());
        layout.addView(button);
    }
    String random() {
        byte[] value = new byte[32]; new SecureRandom().nextBytes(value);
        return Base64.encodeToString(value, Base64.URL_SAFE | Base64.NO_PADDING | Base64.NO_WRAP);
    }
    String enc(String value) { return URLEncoder.encode(value, StandardCharsets.UTF_8); }
    void show(String value) {
        // Only result summaries: never log auth URLs, codes, tokens or keys.
        Log.i("NS8X509TEST", value);
        runOnUiThread(() -> status.setText(value));
    }
    void login(boolean customTab, boolean embedded) {
        try {
            verifier = random(); state = random();
            String challenge = Base64.encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.getBytes(StandardCharsets.US_ASCII)), Base64.URL_SAFE | Base64.NO_WRAP | Base64.NO_PADDING);
            String url = config.getString("issuer") + "/protocol/openid-connect/auth?client_id=android-x509-test&response_type=code&scope=openid&redirect_uri=" + enc(redirect)
                + "&state=" + enc(state) + "&code_challenge_method=S256&code_challenge=" + enc(challenge) + "&prompt=login";
            if (embedded) {
                WebView web = new WebView(this);
                web.getSettings().setJavaScriptEnabled(true);
                web.setWebViewClient(new WebViewClient() {
                    @Override public boolean shouldOverrideUrlLoading(WebView view, String target) {
                        if (target.startsWith(redirect)) { callback(Uri.parse(target)); layout.removeView(web); web.destroy(); return true; }
                        return false;
                    }
                    @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, android.net.http.SslError error) {
                        // Local fixture only: require the exact pinned server cert,
                        // never globally trust a test CA or arbitrary SSL errors.
                        try {
                            byte[] actual = android.net.http.SslCertificate.saveState(error.getCertificate()).getByteArray("x509-certificate");
                            if ("localhost".equals(Uri.parse(error.getUrl()).getHost()) && MessageDigest.isEqual(actual, server.getEncoded())) handler.proceed();
                            else handler.cancel();
                        } catch (Exception e) { handler.cancel(); }
                    }
                    @Override public void onReceivedClientCertRequest(WebView view, ClientCertRequest request) {
                        KeyChain.choosePrivateKeyAlias(MainActivity.this, alias -> {
                            if (alias == null) { request.cancel(); return; }
                            new Thread(() -> {
                                try {
                                    java.security.PrivateKey key = KeyChain.getPrivateKey(MainActivity.this, alias);
                                    X509Certificate[] chain = KeyChain.getCertificateChain(MainActivity.this, alias);
                                    runOnUiThread(() -> request.proceed(key, chain));
                                } catch (Exception e) { runOnUiThread(() -> request.cancel()); }
                            }).start();
                        }, request.getKeyTypes(), request.getPrincipals(), request.getHost(), request.getPort(), null);
                    }
                });
                layout.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
                web.loadUrl(url);
            } else {
                Intent browser = new Intent(Intent.ACTION_VIEW, Uri.parse(url)).setPackage("com.android.chrome");
                if (customTab) {
                    Bundle extras = new Bundle();
                    extras.putBinder("android.support.customtabs.extra.SESSION", null);
                    browser.putExtras(extras);
                }
                startActivity(browser);
            }
        } catch (Exception e) { show("LOGIN FAILED: " + e.getClass().getSimpleName()); }
    }
    @Override public void onNewIntent(Intent intent) { super.onNewIntent(intent); callback(intent.getData()); }
    void callback(Uri uri) {
        if (uri == null || state == null || !state.equals(uri.getQueryParameter("state"))) { show("STATE REJECTED"); return; }
        String code = uri.getQueryParameter("code");
        if (code == null) { show("AUTHORIZATION REJECTED"); return; }
        String pkce = verifier; state = null; verifier = null;
        new Thread(() -> {
            try {
                KeyStore store = KeyStore.getInstance(KeyStore.getDefaultType()); store.load(null);
                store.setCertificateEntry("fixture", server);
                TrustManagerFactory tm = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm()); tm.init(store);
                SSLContext ssl = SSLContext.getInstance("TLS"); ssl.init(null, tm.getTrustManagers(), null);
                HttpsURLConnection conn = (HttpsURLConnection) new java.net.URL(config.getString("issuer") + "/protocol/openid-connect/token").openConnection();
                conn.setSSLSocketFactory(ssl.getSocketFactory()); conn.setConnectTimeout(15000); conn.setReadTimeout(15000);
                conn.setRequestMethod("POST"); conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded");
                String form = "grant_type=authorization_code&client_id=android-x509-test&redirect_uri=" + enc(redirect) + "&code_verifier=" + enc(pkce) + "&code=" + enc(code);
                conn.getOutputStream().write(form.getBytes(StandardCharsets.UTF_8));
                int result = conn.getResponseCode();
                if (result == 200) {
                    JSONObject body = new JSONObject(new String(conn.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
                    show(body.has("access_token") && body.has("id_token") ? "OIDC PKCE TOKEN SUCCESS" : "TOKEN RESPONSE INCOMPLETE");
                } else show("TOKEN REJECTED HTTP " + result);
                conn.disconnect();
            } catch (Exception e) { show("TOKEN FAILED: " + e.getClass().getSimpleName()); }
        }).start();
    }
}
