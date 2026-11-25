#!/usr/bin/env bash
# How Lira 7.4.0 was assembled (paths are the ones used in the build session).
# Inputs: decoded 7.3.1 app (apktool d), lira_7_4_0_app.html, the Java sources here, the release keystore.
set -euo pipefail
BT=${BT:-/tmp/claude-0/tools/bt/android-14}          # build-tools (zipalign, apksigner, dexdump, aapt2)
AJ=${AJ:-/tmp/claude-0/tools/plat/android-34/android.jar}
R8=${R8:-/tmp/claude-0/tools/r8-8.7.18.jar}           # D8 from build-tools 34 crashes on JDK 21 class files
DEC=${DEC:-/tmp/claude-0/work/apk}                    # apktool-decoded app, MainActivity.smali already patched
BASE=${BASE:-../Lira_7_3_1.apk}                       # resources and everything else come from here unchanged
KS=${KS:?path to release.keystore}; OUT=${OUT:-Lira_7_4_0.apk}
HERE=$(cd "$(dirname "$0")/.." && pwd); W=$(mktemp -d)
java -jar apktool.jar b -o "$W/smali.apk" "$DEC" && unzip -qo "$W/smali.apk" classes.dex -d "$W/d1"
mkdir "$W/cls" && javac -source 8 -target 8 -nowarn -encoding UTF-8 -bootclasspath "$AJ" -d "$W/cls" $(find "$HERE/src/main/java" -name '*.java')
(cd "$W/cls" && jar cf ../native.jar com)
mkdir "$W/dex" && java -cp "$R8" com.android.tools.r8.D8 --release --min-api 23 --lib "$AJ" --output "$W/dex" "$W/d1/classes.dex" "$W/native.jar"
unzip -qo -p "$BASE" AndroidManifest.xml > "$W/m_in.xml"
python3 "$HERE/tools/manifest74.py" "$W/m_in.xml" "$W/AndroidManifest.xml" 17 7.4.0
python3 - "$BASE" "$W" <<'PY'
import sys, zipfile
src = zipfile.ZipFile(sys.argv[1]); w = sys.argv[2]; out = zipfile.ZipFile(w + '/unaligned.apk', 'w')
repl = {'classes.dex': open(w + '/dex/classes.dex', 'rb').read(), 'AndroidManifest.xml': open(w + '/AndroidManifest.xml', 'rb').read()}
for i in src.infolist():
    if i.filename.startswith('META-INF/'): continue
    zi = zipfile.ZipInfo(i.filename, date_time=i.date_time); zi.compress_type = i.compress_type; zi.external_attr = i.external_attr
    out.writestr(zi, repl.get(i.filename, src.read(i.filename)))
out.close()
PY
"$BT/zipalign" -p -f 4 "$W/unaligned.apk" "$W/aligned.apk"
"$BT/apksigner" sign --ks "$KS" --ks-type PKCS12 --ks-key-alias notes --min-sdk-version 23 --out "$OUT" "$W/aligned.apk"
"$BT/apksigner" verify --verbose "$OUT"
