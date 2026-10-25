#!/bin/bash
# Crea dist/tk-iscrizioni-<versione>-mac-<arch>.dmg. Da eseguire su un Mac (o sul runner macOS di GitHub).
# Uso: bash mac/build_mac.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
ARCH="$(uname -m)"
PY="${PYTHON:-python3}"
VERSION="$($PY -c "import re;print(re.search(r'VERSION = \"(.+)\"', open('tkiscrizioni/__init__.py').read()).group(1))")"
echo "== tk-iscrizioni $VERSION per macOS ($ARCH)"

$PY -m venv .venv-mac
# shellcheck disable=SC1091
source .venv-mac/bin/activate
python -m pip install --quiet --upgrade pip
python -m pip install --quiet "pyside6-essentials==6.11.*" certifi pyinstaller

echo "== test del motore e dell'interfaccia (finto server IMAP)"
QT_QPA_PLATFORM=offscreen python tests/test_core.py
QT_QPA_PLATFORM=offscreen python tests/test_ui_scan.py

echo "== icona"
python tools_make_icon.py --iconset
iconutil -c icns assets/tk-iscrizioni.iconset -o assets/tk-iscrizioni.icns

echo "== app"
rm -rf build dist
# testi delle licenze (AGPL + componenti inclusi + COMPONENTI.txt): lo spec li mette in Contents/Resources/licenze
python tools_licenze.py "$ROOT/build/licenze" mac
pyinstaller --noconfirm --clean mac/tk-iscrizioni-mac.spec
APP="dist/tk-iscrizioni.app"
# PyInstaller 6 mette i dati in Contents/Resources (con un collegamento in Contents/Frameworks)
for f in COPYING-AGPL-3.0.txt COMPONENTI.txt LGPL-3.0.txt; do
    [ -f "$APP/Contents/Resources/licenze/$f" ] || [ -f "$APP/Contents/Frameworks/licenze/$f" ] \
        || { echo "MANCA licenze/$f NELL'APP"; exit 1; }
done
codesign --force --deep --sign - "$APP"

echo "== selftest"
SHOT="$ROOT/dist/selftest-$ARCH.png"
run_selftest() {
    "$APP/Contents/MacOS/tk-iscrizioni" --selftest "$SHOT" &
    local pid=$!
    for _ in $(seq 1 60); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
    done
    kill "$pid" 2>/dev/null || true
}
run_selftest
if [ ! -f "$SHOT" ]; then
    echo "   finestra non disponibile, riprovo in modalità offscreen"
    export QT_QPA_PLATFORM=offscreen
    run_selftest
    unset QT_QPA_PLATFORM
fi
[ -f "$SHOT" ] || { echo "SELFTEST FALLITO: l'app non si avvia"; exit 1; }
[ -f "$ROOT/dist/selftest-$ARCH.csv" ] || { echo "SELFTEST FALLITO: l'esportazione non funziona"; exit 1; }
echo "   selftest OK (finestra + esportazione)"

echo "== dmg"
STAGE="$(mktemp -d)"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applicazioni"
cp mac/LEGGIMI.txt "$STAGE/Leggimi - primo avvio.txt"
DMG="dist/tk-iscrizioni-$VERSION-mac-$ARCH.dmg"
for tentativo in 1 2 3 4; do
    if hdiutil create -volname "tk-iscrizioni $VERSION" -srcfolder "$STAGE" -ov -format UDZO "$DMG"; then
        break
    fi
    echo "   hdiutil occupato, riprovo ($tentativo)"
    sleep 6
    [ "$tentativo" = "4" ] && { echo "CREAZIONE DMG FALLITA"; exit 1; }
done
rm -rf "$STAGE"
echo "== Creato $DMG ($(du -h "$DMG" | cut -f1))"

if [ "${SKIP_UPDATE_TEST:-0}" != "1" ]; then
    echo "== test aggiornamento automatico"
    TESTAPP="$HOME/Applications/tk-iscrizioni.app"
    mkdir -p "$HOME/Applications"
    rm -rf "$TESTAPP"
    cp -R "$APP" "$TESTAPP"
    BEFORE="$(stat -f %i "$TESTAPP/Contents/Info.plist")"
    COPY="$(mktemp -d)/tk-iscrizioni-test.dmg"
    cp "$DMG" "$COPY"
    SHA="$(shasum -a 256 "$COPY" | cut -d' ' -f1)"
    MANIFEST="$(mktemp -d)/tk-iscrizioni.json"
    SIZE="$(stat -f %z "$COPY")"
    printf '{"version":"99.0.0","notes":["test"],"mac-%s":{"url":"file://%s","sha256":"%s","size":%s}}' "$ARCH" "$COPY" "$SHA" "$SIZE" > "$MANIFEST"
    # aggiornamenti firmati: chiave usa e getta solo per questo test (la vera resta sul PC di Pietro)
    read -r SEME PUB <<< "$(python mac/firma_aggiornamenti.py prova)"
    TK_FIRMA_SEME_PROVA="$SEME" python mac/firma_aggiornamenti.py firma --slug tk-iscrizioni "$MANIFEST"
    TK_AGGIORNAMENTI_PROVA="$PUB" "$TESTAPP/Contents/MacOS/tk-iscrizioni" --update-test "file://$MANIFEST" --no-relaunch
    AFTER="$BEFORE"
    for _ in $(seq 1 120); do
        if [ -f "$TESTAPP/Contents/Info.plist" ]; then
            AFTER="$(stat -f %i "$TESTAPP/Contents/Info.plist" 2>/dev/null || echo "$BEFORE")"
            [ "$AFTER" != "$BEFORE" ] && break
        fi
        sleep 1
    done
    # cartella dati col nome storico (LEGACY_TITLE)
    cat "$HOME/Library/Application Support/tkISCRIZIONI/aggiornamento.log" 2>/dev/null || true
    if [ "$AFTER" = "$BEFORE" ] || [ ! -x "$TESTAPP/Contents/MacOS/tk-iscrizioni" ]; then
        echo "TEST AGGIORNAMENTO FALLITO"
        exit 1
    fi
    rm -rf "$TESTAPP"
    echo "   aggiornamento OK (bundle sostituito)"
fi
