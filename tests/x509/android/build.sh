#!/bin/bash
# Run from repository root: build.sh FIXTURE_DIRECTORY ANDROID_SDK_DIRECTORY
# Build output and embedded fixture secrets stay in the private fixture folder.
set -euo pipefail
fixture_dir="$(realpath "$1")"
sdk_dir="$(realpath "$2")"
source_dir="$(realpath "$(dirname "$0")")"
build_dir="$fixture_dir/android-build"
mkdir -p "$build_dir/assets" "$build_dir/classes" "$build_dir/dex"
cp "$fixture_dir/server.crt" "$build_dir/assets/server.crt"
cp "$fixture_dir/android-config.json" "$build_dir/assets/config.json"
openssl pkcs12 -export -inkey "$fixture_dir/allowed.key" -in "$fixture_dir/allowed.crt" \
    -name 'NS8 isolated L8 test' -out "$build_dir/assets/identity.p12" -passout pass:ns8-test
podman run --rm -v "$source_dir:/source:ro,Z" -v "$build_dir:/build:Z" -v "$sdk_dir:/sdk:ro,Z" \
  docker.io/library/maven:3.9.16-eclipse-temurin-21 bash -euc '
    javac -source 11 -target 11 -classpath /sdk/platforms/android-35/android.jar -d /build/classes /source/MainActivity.java
    /sdk/build-tools/35.0.0/aapt2 link -o /build/unsigned.apk -I /sdk/platforms/android-35/android.jar --manifest /source/AndroidManifest.xml -A /build/assets
    /sdk/build-tools/35.0.0/d8 --lib /sdk/platforms/android-35/android.jar --min-api 26 --output /build/dex /build/classes/org/nethserver/x509test/*.class
    cd /build/dex
    jar uf /build/unsigned.apk classes.dex
    keytool -genkeypair -keystore /build/test.keystore -storepass ns8-test -keypass ns8-test -alias test -keyalg RSA -dname CN=IsolatedTest -validity 2
    /sdk/build-tools/35.0.0/zipalign -f 4 /build/unsigned.apk /build/aligned.apk
    /sdk/build-tools/35.0.0/apksigner sign --ks /build/test.keystore --ks-pass pass:ns8-test --out /build/ns8-x509-test.apk /build/aligned.apk
  '
printf 'Private test APK: %s\n' "$build_dir/ns8-x509-test.apk"
