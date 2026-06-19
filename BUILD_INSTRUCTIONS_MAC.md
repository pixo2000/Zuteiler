# Anleitung: macOS App erstellen

## Automatisch über GitHub (empfohlen)

Du brauchst **keinen Mac**. Ein GitHub-Actions-Workflow baut die App auf einem
Mac-Server, signiert sie und veröffentlicht sie als **Release**.

So löst du einen Build aus:
- **Einfach**: Änderungen auf den `main`-Branch pushen → es entsteht ein
  Release namens `build-<Nummer>`.
- **Mit Versionsnummer**: Einen Tag pushen, z. B.
  ```bash
  git tag v1.0.0
  git push origin v1.0.0
  ```
  → es entsteht ein Release `v1.0.0`.
- **Manuell**: Auf GitHub unter **Actions → macOS Build & Release →
  "Run workflow"**.

Die fertige `Methodentag-Zuteilung-macOS.zip` findest du danach unter
**Releases** (rechts auf der Repo-Startseite) oder unter **Actions** als
Artefakt.

### Warum war die App vorher "beschädigt"?
- Der alte Workflow lud das `.app`-Bundle direkt hoch. GitHub packt es dann
  erneut in ein ZIP und **zerstört dabei die internen Symlinks/Rechte** – die
  entpackte App war dadurch defekt.
- Außerdem war die App **nicht signiert**, weshalb macOS sie nach dem Download
  als "beschädigt" markiert.

Der neue Workflow **signiert** die App (ad-hoc) und packt sie mit `ditto`, das
die Bundle-Struktur korrekt erhält.

> **Hinweis zu "pip & Co.":** Die Nutzerin braucht **kein** Python und **kein**
> pip auf ihrem Mac. PyInstaller packt den Python-Interpreter und alle
> Abhängigkeiten direkt in die `.app`.

---

## Manuell auf einem Mac (Alternative)

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
1. Die `Methodentag-Zuteilung-macOS.zip` herunterladen und entpacken (Doppelklick)
2. Die `Methodentag Zuteilung.app` in den Ordner **Programme** (Applications) ziehen

### Erste Nutzung
1. **Rechtsklick** auf die App → **"Öffnen"** → erneut **"Öffnen"** bestätigen
   (nur beim ersten Mal nötig)
2. Die App startet automatisch den Browser mit der Anwendung

### ⚠️ Falls macOS meldet: "App ist beschädigt"
Das liegt **nicht** an einem echten Defekt, sondern an der macOS-Sicherheits-
sperre (Gatekeeper) für nicht bei Apple notarisierte Apps. Einmalig im
**Terminal** ausführen (Programme → Dienstprogramme → Terminal):

```bash
xattr -cr "/Applications/Methodentag Zuteilung.app"
```

Danach die App per **Rechtsklick → Öffnen** starten.

### Nutzung
- **Starten**: Doppelklick auf die App
- **Beenden**: Schließe das Browser-Fenster oder beende die App (Cmd+Q)

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
