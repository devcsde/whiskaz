#!/usr/bin/env bash
# Baut dist/whiskaz.app und dist/whiskaz-<version>-macos.zip. Läuft nur auf macOS.
#
# Voraussetzungen: Xcode-Kommandozeilentools (für iconutil), Python 3.10+ und librsvg:
#   brew install librsvg
set -euo pipefail

die() { echo "Fehler: $*" >&2; exit 1; }

[[ "$(uname -s)" == "Darwin" ]] || die "Dieses Skript läuft nur auf macOS."
command -v rsvg-convert >/dev/null || die "librsvg fehlt: brew install librsvg"
command -v iconutil >/dev/null || die "iconutil fehlt: xcode-select --install"
command -v python3 >/dev/null || die "python3 fehlt"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")"
SVG="src/whiskaz/assets/whiskaz.svg"
ICONSET="build/macos/whiskaz.iconset"
ICNS="packaging/macos/whiskaz.icns"

echo "==> Erzeuge Icon"
rm -rf "$ICONSET"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    rsvg-convert -w "$size" -h "$size" "$SVG" -o "$ICONSET/icon_${size}x${size}.png"
    rsvg-convert -w "$((size * 2))" -h "$((size * 2))" "$SVG" -o "$ICONSET/icon_${size}x${size}@2x.png"
done
iconutil -c icns "$ICONSET" -o "$ICNS"

echo "==> Erzeuge Build-Umgebung"
VENV="build/macos/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet "$ROOT" pyinstaller

echo "==> Baue whiskaz.app mit PyInstaller"
rm -rf dist/whiskaz.app
"$VENV/bin/pyinstaller" --noconfirm --clean \
    --distpath dist --workpath build/macos/pyinstaller \
    packaging/macos/whiskaz.spec

echo "==> Packe ZIP"
ZIP="dist/whiskaz-${VERSION}-macos.zip"
rm -f "$ZIP"
ditto -c -k --keepParent dist/whiskaz.app "$ZIP"

echo "==> Fertig"
echo "App:  $ROOT/dist/whiskaz.app"
echo "ZIP:  $ROOT/$ZIP"
echo
echo "Hinweis: Die App ist nicht signiert. Beim ersten Start blockiert macOS sie."
echo "Lösung: Rechtsklick auf whiskaz.app, dann „Öffnen“. Alternativ im Terminal:"
echo "  xattr -dr com.apple.quarantine dist/whiskaz.app"
