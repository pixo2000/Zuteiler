# Anleitung: macOS App erstellen

## Für dich (als Entwickler)

### Voraussetzungen
Du brauchst Zugang zu einem Mac, um die `.app`-Datei zu bauen.

### Build-Prozess

1. **Auf dem Mac**: Navigiere zum Projektordner
   ```bash
   cd /pfad/zum/Methodentag
   ```

2. **Installiere Requirements**
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Führe das Build-Script aus**
   ```bash
   ./build_mac.sh
   ```

4. **Ergebnis**: Im `dist/` Ordner findest du die `Methodentag Zuteilung.app`

### Alternative: Manueller Build
Falls das Script nicht funktioniert:
```bash
pyinstaller build_mac.spec
```

---

## Für die Lehrerin (Nutzerin)

### Installation
1. Kopiere die `Methodentag Zuteilung.app` auf deinen Mac
2. Lege sie z.B. in den `Programme` (Applications) Ordner oder auf den Desktop

### Erste Nutzung
1. **Doppelklick** auf die App
2. Falls eine Warnung erscheint ("App von nicht verifiziertem Entwickler"):
   - **Rechtsklick** auf die App
   - Wähle **"Öffnen"**
   - Bestätige mit **"Öffnen"**
   - Dies musst du nur beim ersten Mal machen!

3. Die App startet automatisch deinen Browser mit der Anwendung

### Nutzung
- **Starten**: Doppelklick auf die App
- **Beenden**: Schließe das Browser-Fenster oder beende die App (Cmd+Q)
- **Daten**: Lege deine `daten.csv` in denselben Ordner wie die App

---

## Hinweise für Entwickler

### Was wird in die App gepackt?
- Python Interpreter
- Alle Dependencies (Flask, pandas, etc.)
- Templates und Daten
- Die CSV-Datei

### Größe
Die `.app`-Datei wird ca. 50-100 MB groß sein.

### Testen
Teste die App auf einem echten Mac, bevor du sie weitergibst!

### Icon (Optional)
1. Erstelle ein `.icns` Icon (macOS Icon-Format)
2. Speichere es als `icon.icns` im Projektordner
3. Ändere in `build_mac.spec`: `icon='icon.icns'`

### Code-Signierung (Optional, für professionelle Apps)
Um die Sicherheitswarnung zu vermeiden, bräuchtest du:
- Einen Apple Developer Account ($99/Jahr)
- Ein Code Signing Certificate
- Notarisierung der App

Für eine schulinterne App ist das aber übertrieben.

---

## Troubleshooting

### "App kann nicht geöffnet werden"
→ Rechtsklick → Öffnen (siehe oben)

### "App beschädigt"
→ Terminal öffnen und eingeben:
```bash
xattr -cr "/pfad/zur/Methodentag Zuteilung.app"
```

### Browser öffnet nicht automatisch
→ Öffne manuell: http://localhost:5000
