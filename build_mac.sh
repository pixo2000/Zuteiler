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
    echo ""
    echo "✅ Erfolgreich gebaut!"
    echo ""
    echo "Die App befindet sich in: dist/Methodentag Zuteilung.app"
    echo ""
    echo "📝 Anleitung für die Lehrerin:"
    echo "1. Kopiere den Ordner 'Methodentag Zuteilung.app' auf ihren Mac"
    echo "2. Sie kann die App per Doppelklick starten"
    echo "3. Beim ersten Start muss sie evtl. Rechtsklick -> Öffnen machen"
    echo "   (wegen macOS Sicherheitseinstellungen)"
    echo ""
else
    echo ""
    echo "❌ Build fehlgeschlagen. Bitte prüfe die Fehler oben."
    exit 1
fi
