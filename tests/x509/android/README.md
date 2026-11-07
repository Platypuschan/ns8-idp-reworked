# Repeat the isolated Android test

This is a disposable Android 13 test app, not a production application or a
Bitwarden build. It exercises Chrome, Custom Tabs and a KeyChain-aware WebView,
checks the callback state, then redeems the code using S256 PKCE. It logs only a
result summary, never tokens, codes or authentication URLs.

From the repository root, first install the dependencies/build the fixture
images listed in `docs/CERTIFICATES.md`. Then run:

```sh
X509_KEEP=1 python3 tests/x509/run.py
```

The successful suite prints a private fixture directory. In the following
commands replace `/tmp/ns8-x509-EXAMPLE` and the SDK directory with actual paths:

```sh
python3 tests/x509/android/prepare.py /tmp/ns8-x509-EXAMPLE
bash tests/x509/android/build.sh /tmp/ns8-x509-EXAMPLE /absolute/path/to/android-sdk
```

The SDK needs platform android-35 and build-tools 35.0.0; Java compilation uses
the pinned Maven container. `prepare.py` prints the loopback TLS port. For the
explicit ADB device, map that same port in both directions with `adb -s DEVICE
reverse tcp:PORT tcp:PORT`, then install the private APK at
`FIXTURE/android-build/ns8-x509-test.apk`. Open the test app, install its client
identity using **VPN and apps**, export password `ns8-test`, then select each
login method. Chrome warns about the fixture's self-signed **server** certificate;
the exception must be restricted to localhost. No global server CA is installed.
The native token request and WebView pin the exact fixture server certificate.

Do not publish the APK, PKCS#12, keystore, private fixture metadata or raw UI dumps.
The app embeds an isolated short-lived test identity. It preserves other apps'
accounts and configuration. Test AD group removal and device pin revocation in
the fixture; normal app sessions/offline data have separate lifecycle rules.

Cleanup: remove only **NS8 isolated L8 test** in Android user credentials, uninstall
`org.nethserver.x509test`, remove only this `adb reverse` port, and run:

```sh
python3 tests/x509/android/cleanup.py /tmp/ns8-x509-EXAMPLE
```

Never clear all Android credentials or any existing application data.
