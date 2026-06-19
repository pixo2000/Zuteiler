#!/bin/bash

echo "🚀 Baue macOS App für Methodentag Zuteilung..."
echo ""

# Prüfe ob wir auf macOS sind
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  WARNUNG: Dieses Script sollte auf einem Mac ausgeführt werden!"
    echo "   Du kannst die App trotzdem bauen, aber sie wird nur auf macOS funktionieren."
    echo ""
fi

# Installiere PyInstaller falls nicht vorhanden
echo "📦 Installiere PyInstaller..."
pip install pyinstaller

# Bereinige alte Builds
echo "🧹 Bereinige alte Builds..."
rm -rf build dist

# Baue die App
echo "🔨 Baue die App..."
pyinstaller build_mac.spec

# Prüfe ob erfolgreich
if [ -d "dist/Methodentag Zuteilung.app" ]; then
    # Ad-hoc-Signatur, damit macOS die App nicht als "beschädigt" meldet
    echo "🔏 Signiere App (ad-hoc)..."
    codesign --force --deep --sign - "dist/Methodentag Zuteilung.app"

    # Mit ditto verpacken (erhält Symlinks/Rechte im .app-Bundle)
    echo "📦 Verpacke App als ZIP..."
    rm -f "Methodentag-Zuteilung-macOS.zip"
    ditto -c -k --sequesterRsrc --keepParent \
        "dist/Methodentag Zuteilung.app" \
        "Methodentag-Zuteilung-macOS.zip"

    echo ""
    echo "✅ Erfolgreich gebaut!"
    echo ""
    echo "Die App befindet sich in: dist/Methodentag Zuteilung.app"
    echo "Versand-ZIP: Methodentag-Zuteilung-macOS.zip"
    echo ""
    echo "📝 Anleitung für die Lehrerin:"
    echo "1. ZIP entpacken und die App in den Ordner 'Programme' ziehen"
    echo "2. Falls 'App ist beschädigt': im Terminal ausführen:"
    echo "     xattr -cr \"/Applications/Methodentag Zuteilung.app\""
    echo "3. Danach Rechtsklick -> Öffnen (nur beim ersten Mal nötig)"
    echo ""
else
    echo ""
    echo "❌ Build fehlgeschlagen. Bitte prüfe die Fehler oben."
    exit 1
fi
