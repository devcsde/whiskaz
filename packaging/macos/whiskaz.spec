# PyInstaller-Spezifikation für whiskaz.app
# Aufruf über scripts/build-mac-app.sh (dort wird auch das Icon erzeugt).

import tomllib
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parents[1]
with open(ROOT / "pyproject.toml", "rb") as f:
    VERSION = tomllib.load(f)["project"]["version"]

a = Analysis(
    [str(ROOT / "src" / "whiskaz" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[(str(ROOT / "src" / "whiskaz" / "assets" / "whiskaz.svg"), "whiskaz/assets")],
    hiddenimports=["pynput.keyboard._darwin", "pynput._util.darwin"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="whiskaz",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ROOT / "packaging" / "macos" / "whiskaz.icns"),
)

coll = COLLECT(exe, a.binaries, a.datas, name="whiskaz", strip=False, upx=False)

app = BUNDLE(
    coll,
    name="whiskaz.app",
    icon=str(ROOT / "packaging" / "macos" / "whiskaz.icns"),
    bundle_identifier="de.whiskaz.app",
    info_plist={
        "CFBundleName": "whiskaz",
        "CFBundleDisplayName": "whiskaz",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # Ohne diesen Text stürzt die App beim ersten Mikrofonzugriff ab.
        "NSMicrophoneUsageDescription": "whiskaz nimmt Sprache auf, solange du die Diktier-Taste hältst oder die Aufnahme läuft.",
        # Bewusst kein LSUIElement: whiskaz soll im Dock erscheinen.
    },
)
