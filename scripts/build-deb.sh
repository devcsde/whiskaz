#!/usr/bin/env bash
# Baut dist/whiskaz_<version>-1_<arch>.deb
#
# Das Paket enthält eine fertige venv unter /opt/whiskaz/venv mit allen Python-Abhängigkeiten.
# Die Wheels sind an Python-Version und Architektur gebunden. Deshalb auf dem Zielsystem
# (oder einer gleichen Debian-/Ubuntu-Version) bauen.
set -euo pipefail

die() { echo "Fehler: $*" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

command -v dpkg-deb >/dev/null || die "dpkg-deb fehlt (Paket dpkg-dev)."
python3 -m venv --help >/dev/null 2>&1 || die "python3-venv fehlt: sudo apt install python3-venv"

VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml', 'rb'))['project']['version'])")"
ARCH="$(dpkg --print-architecture)"
PKG="whiskaz"
DEB_VERSION="${VERSION}-1"
STAGE="$ROOT/build/deb/${PKG}_${DEB_VERSION}_${ARCH}"
OUT="$ROOT/dist"

echo "==> Baue ${PKG} ${DEB_VERSION} (${ARCH})"
rm -rf "$STAGE"
mkdir -p \
    "$STAGE/DEBIAN" \
    "$STAGE/opt/whiskaz" \
    "$STAGE/usr/bin" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/icons/hicolor/scalable/apps" \
    "$STAGE/usr/share/doc/$PKG"

echo "==> Erzeuge venv mit Abhängigkeiten (kann einige Minuten dauern)"
VENV="$STAGE/opt/whiskaz/venv"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --no-cache-dir --upgrade pip
"$VENV/bin/pip" install --quiet --no-cache-dir "$ROOT"
# Skripte wie pip, activate oder whiskaz tragen den Build-Pfad im Shebang bzw. im Skript.
# Der Launcher unten ruft python -m whiskaz direkt auf, deshalb werden sie nicht gebraucht.
find "$VENV/bin" -mindepth 1 -maxdepth 1 ! -name 'python*' -delete

echo "==> Installiere Launcher, Desktop-Eintrag und Icon"
cat > "$STAGE/usr/bin/$PKG" <<'EOF'
#!/bin/sh
exec /opt/whiskaz/venv/bin/python -m whiskaz "$@"
EOF
chmod 755 "$STAGE/usr/bin/$PKG"
install -m 644 packaging/whiskaz.desktop "$STAGE/usr/share/applications/$PKG.desktop"
install -m 644 src/whiskaz/assets/whiskaz.svg "$STAGE/usr/share/icons/hicolor/scalable/apps/$PKG.svg"
install -m 644 packaging/copyright "$STAGE/usr/share/doc/$PKG/copyright"

echo "==> Schreibe control-Datei"
INSTALLED_KB="$(du -sk "$STAGE" | cut -f1)"
cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $DEB_VERSION
Architecture: $ARCH
Maintainer: whiskaz <whiskaz@localhost>
Installed-Size: $INSTALLED_KB
Section: sound
Priority: optional
Depends: python3 (>= 3.10), libportaudio2, libgl1, libegl1, libxkbcommon0, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0, libxcb-xkb1, libdbus-1-3, libfontconfig1
Description: Lokales Push-to-talk-Diktat
 whiskaz wandelt Sprache lokal in Text um, ohne Cloud-Dienst.
 Solange die Taste gedrückt ist, wird aufgenommen. Beim Loslassen
 wird der erkannte Text an der aktuellen Cursorposition eingefügt.
 Enthält ein Wörterbuch für Namen und Fachbegriffe sowie einen
 durchsuchbaren Verlauf.
 .
 Die Spracherkennung läuft mit faster-whisper. Modelle werden beim
 ersten Gebrauch heruntergeladen.
EOF

echo "==> Baue Paket"
mkdir -p "$OUT"
DEB_FILE="$OUT/${PKG}_${DEB_VERSION}_${ARCH}.deb"
dpkg-deb --build --root-owner-group "$STAGE" "$DEB_FILE" >/dev/null

if command -v lintian >/dev/null; then
    echo "==> lintian"
    lintian --no-tag-display-limit "$DEB_FILE" || true
fi

echo "==> Fertig: $DEB_FILE"
ls -lh "$DEB_FILE"
