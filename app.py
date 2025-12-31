from flask import Flask, render_template, request, jsonify, send_file
import os
import sys
import csv
from main import Student, Course, assign_students_to_courses, export_results, export_summary_txt
import io
from collections import Counter
from datetime import datetime
import pandas as pd
import random
import socket
import platform
import tempfile
import atexit
import shutil
import threading
import webbrowser

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Betriebssystem-abhängige Konfiguration
# macOS und Linux: Nur RAM, keine persistente Speicherung
# Windows: Persistente Speicherung im data-Ordner
IS_RAM_ONLY_MODE = platform.system() in ['Darwin', 'Linux']

if IS_RAM_ONLY_MODE:
    # RAM-only Modus: Verwende temporäres Verzeichnis
    TEMP_DIR = tempfile.mkdtemp(prefix='methodentag_')
    UPLOADS_DIR = None
    RESULTS_DIR = TEMP_DIR
    
    # Cleanup beim Beenden
    def cleanup_temp_dir():
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
            print(f"🗑️  Temporäres Verzeichnis gelöscht: {TEMP_DIR}")
    
    atexit.register(cleanup_temp_dir)
    print(f"🔒 RAM-Only Modus aktiviert (macOS/Linux)")
    print(f"   Temporäres Verzeichnis: {TEMP_DIR}")
else:
    # Verzeichnis für persistente Datenspeicherung (nicht über Web zugänglich)
    DATA_DIR = os.path.join(SCRIPT_DIR, 'data')
    UPLOADS_DIR = os.path.join(DATA_DIR, 'uploads')
    RESULTS_DIR = os.path.join(DATA_DIR, 'results')
    
    # Erstelle Verzeichnisse falls sie nicht existieren
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print("💾 Persistente Speicherung aktiviert (Windows)")

# Globale Variable für aktuelle Daten (im RAM für schnellen Zugriff)
current_data = {
    'students': None,
    'courses': None,
    'filename': None,
    'upload_path': None  # Pfad zur gespeicherten Upload-Datei
}

# Timer für automatisches Löschen der Dateien (nur im RAM-Only Modus)
AUTO_DELETE_MINUTES = 10
delete_timer = None
delete_timestamp = None

def delete_temp_files():
    """Löscht die temporären Download-Dateien nach Ablauf der Zeit"""
    global delete_timestamp
    if IS_RAM_ONLY_MODE and RESULTS_DIR and os.path.exists(RESULTS_DIR):
        print(f"⏰ Auto-Delete Timer abgelaufen - lösche temporäre Dateien")
        for filename in ['zuteilung_schueler.csv', 'zuteilung_kurse.csv', 'zusammenfassung.txt']:
            filepath = os.path.join(RESULTS_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"   🗑️  Gelöscht: {filename}")
        delete_timestamp = None

def start_delete_timer():
    """Startet den Timer für automatisches Löschen"""
    global delete_timer, delete_timestamp
    
    # Stoppe vorherigen Timer falls vorhanden
    if delete_timer is not None:
        delete_timer.cancel()
    
    if IS_RAM_ONLY_MODE:
        delete_timestamp = datetime.now().timestamp() + (AUTO_DELETE_MINUTES * 60)
        delete_timer = threading.Timer(AUTO_DELETE_MINUTES * 60, delete_temp_files)
        delete_timer.daemon = True
        delete_timer.start()
        print(f"⏰ Auto-Delete Timer gestartet: Dateien werden in {AUTO_DELETE_MINUTES} Minuten gelöscht")

def load_data_from_csv_content(file_content):
    """Lädt CSV-Daten direkt aus dem Speicher"""
    students = []
    all_courses = set()
    
    # Dekodiere Bytes zu String falls nötig
    if isinstance(file_content, bytes):
        file_content = file_content.decode('utf-8')
    
    # Verwende StringIO für In-Memory CSV-Parsing
    csv_file = io.StringIO(file_content)
    reader = csv.reader(csv_file, delimiter=';')
    
    # Überspringe die Kopfzeile
    next(reader, None)
    
    for row in reader:
        # Stelle sicher, dass die Zeile genug Spalten hat
        if len(row) < 7:
            continue
        
        # Spalten: 0=Nachname, 1=Vorname, 2=Klasse, 3-6=Wünsche 1-4
        lastname = row[0].strip()
        firstname = row[1].strip()
        klasse = row[2].strip()
        
        # Ignoriere Zeilen mit "unbekannt" oder "unknown" als Klasse (case-insensitive)
        if klasse.lower() in ['unbekannt', 'unknown']:
            continue
        
        # Sammle die Wünsche aus Spalten 3-6
        wishes = []
        for i in range(3, 7):
            if row[i] and row[i].strip():
                wish = row[i].strip()
                wishes.append(wish)
                all_courses.add(wish)
        
        student = Student(lastname, firstname, klasse, wishes)
        students.append(student)
    
    # Erstelle Course-Objekte
    courses = {name: Course(name) for name in all_courses}
    
    return students, courses

def load_data_from_file(filepath):
    """Lädt die CSV-Datei von Disk (Fallback für daten.csv)"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    return load_data_from_csv_content(content)

@app.route('/')
def index():
    return render_template('index.html', ram_only_mode=IS_RAM_ONLY_MODE, os_name=platform.system())

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Lädt eine CSV-Datei hoch und speichert sie persistent im data/uploads Verzeichnis"""
    print("=" * 60)
    print("📤 UPLOAD REQUEST empfangen")
    print(f"Request files: {request.files}")
    print(f"Request form: {request.form}")
    print(f"Request method: {request.method}")
    print(f"Content-Type: {request.content_type}")
    
    if 'file' not in request.files:
        error_msg = 'Keine Datei im Request gefunden (key "file" fehlt)'
        print(f"❌ ERROR: {error_msg}")
        print(f"Verfügbare Keys: {list(request.files.keys())}")
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400
    
    file = request.files['file']
    print(f"📁 Datei gefunden: {file.filename}")
    
    if file.filename == '':
        error_msg = 'Dateiname ist leer'
        print(f"❌ ERROR: {error_msg}")
        return jsonify({
            'success': False,
            'error': 'Keine Datei ausgewählt'
        }), 400
    
    # Prüfe Dateiendung
    if not file.filename.lower().endswith('.csv'):
        error_msg = f'Ungültiger Dateityp: {file.filename}'
        print(f"❌ ERROR: {error_msg}")
        return jsonify({
            'success': False,
            'error': 'Ungültiger Dateityp. Nur CSV-Dateien sind erlaubt.'
        }), 400
    
    try:
        # Lese Datei direkt in den Speicher
        print("📖 Lese Dateiinhalt...")
        file_content = file.read()
        print(f"✓ Datei gelesen: {len(file_content)} Bytes")
        
        # Speichere Datei nur auf Windows persistent
        upload_path = None
        if not IS_RAM_ONLY_MODE:
            # Erstelle Zeitstempel für eindeutigen Dateinamen
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"
            upload_path = os.path.join(UPLOADS_DIR, safe_filename)
            
            # Speichere Datei persistent
            print(f"💾 Speichere Datei nach: {upload_path}")
            with open(upload_path, 'wb') as f:
                f.write(file_content)
            print(f"✓ Datei gespeichert")
        else:
            print(f"🔒 RAM-Only Modus: Datei wird NICHT gespeichert")
        
        # Versuche die Daten zu laden und zu validieren
        print("🔄 Parse CSV-Daten...")
        students, courses = load_data_from_csv_content(file_content)
        print(f"✓ CSV geparst: {len(students)} Schüler, {len(courses)} Kurse")
        
        # Speichere in globaler Variable für schnellen Zugriff
        current_data['students'] = students
        current_data['courses'] = courses
        current_data['filename'] = file.filename
        current_data['upload_path'] = upload_path
        
        print("✅ Upload erfolgreich!")
        print("=" * 60)
        
        return jsonify({
            'success': True,
            'filename': file.filename,
            'studentCount': len(students),
            'courseCount': len(courses)
        })
    except Exception as e:
        error_msg = f'Fehler beim Laden der Datei: {str(e)}'
        print(f"❌ EXCEPTION: {error_msg}")
        print(f"Exception type: {type(e).__name__}")
        import traceback
        print(traceback.format_exc())
        print("=" * 60)
        return jsonify({
            'success': False,
            'error': error_msg
        }), 400

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analysiert die Daten ohne Zuteilung durchzuführen"""
    try:
        # Prüfe ob Daten hochgeladen wurden
        if current_data['students'] is None or current_data['courses'] is None:
            return jsonify({
                'success': False,
                'error': 'Bitte laden Sie zuerst eine CSV-Datei hoch.'
            }), 400
        
        students = current_data['students']
        courses = current_data['courses']
        
        # Sammle Kursstatistiken
        course_list = []
        for name in sorted(courses.keys()):
            # Zähle wie oft dieser Kurs gewünscht wurde
            wish_count = 0
            wish_priorities = {1: 0, 2: 0, 3: 0, 4: 0}
            for student in students:
                for i, wish in enumerate(student.wishes, 1):
                    if wish == name:
                        wish_count += 1
                        wish_priorities[i] += 1
            
            course_list.append({
                'name': name,
                'wishCount': wish_count,
                'priorities': wish_priorities
            })
        
        return jsonify({
            'success': True,
            'studentCount': len(students),
            'courseCount': len(courses),
            'courses': course_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/assign', methods=['POST'])
def assign():
    """Führt die Zuteilung durch"""
    try:
        data = request.get_json()
        max_students = data.get('maxStudents')
        equal_distribution = data.get('equalDistribution', False)
        course_limits = data.get('courseLimits', {})  # Individuelle Limits pro Kurs
        
        # Konvertiere max_students (globales Limit)
        if max_students is not None and max_students != '':
            max_students = int(max_students)
        else:
            max_students = None
        
        # Prüfe ob Daten hochgeladen wurden
        if current_data['students'] is None or current_data['courses'] is None:
            return jsonify({
                'success': False,
                'error': 'Bitte laden Sie zuerst eine CSV-Datei hoch.'
            }), 400
        
        # Erstelle neue Course-Objekte für die Zuteilung (Deep Copy)
        students = current_data['students']
        courses = {name: Course(name) for name in current_data['courses'].keys()}
        
        # Setze alle Zuweisungen zurück
        for student in students:
            student.assigned_courses = []
            student.fulfilled_wish_numbers = []
        
        fulfilled_wishes, unfulfilled_students, total_wishes = assign_students_to_courses(
            students, courses, max_students, equal_distribution, course_limits
        )
        
        # Exportiere Ergebnisse
        if not IS_RAM_ONLY_MODE:
            # Windows: Speichere persistent in results Verzeichnis + Kopie für Downloads
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_subdir = os.path.join(RESULTS_DIR, timestamp)
            os.makedirs(result_subdir, exist_ok=True)
            
            print(f"💾 Speichere Ergebnisse nach: {result_subdir}")
            export_results(students, courses, output_dir=result_subdir)
            export_summary_txt(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes, max_students, output_dir=result_subdir)
            
            # Kopiere die Dateien auch ins Hauptverzeichnis für die Download-API
            for filename in ['zuteilung_schueler.csv', 'zuteilung_kurse.csv', 'zusammenfassung.txt']:
                src = os.path.join(result_subdir, filename)
                dst = os.path.join(SCRIPT_DIR, filename)
                shutil.copy2(src, dst)
        else:
            # macOS/Linux: Nur temporär im temp-Verzeichnis speichern
            print(f"🔒 RAM-Only Modus: Temporäre Dateien im RAM-Verzeichnis")
            export_results(students, courses, output_dir=RESULTS_DIR)
            export_summary_txt(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes, max_students, output_dir=RESULTS_DIR)
            
            # Starte Auto-Delete Timer
            start_delete_timer()
        
        # Berechne Statistiken
        total_fulfilled = sum(fulfilled_wishes.values())
        fulfillment_rate = (total_fulfilled / total_wishes * 100) if total_wishes > 0 else 0
        
        wishes_per_student = Counter()
        for student in students:
            num_fulfilled = len(student.fulfilled_wish_numbers)
            wishes_per_student[num_fulfilled] += 1
        
        students_without_wishes = [s for s in students if not s.fulfilled_wish_numbers]
        
        # Kursgrößen
        course_stats = []
        for course_name, course in sorted(courses.items()):
            total = course.get_total_students()
            t0 = course.get_students_in_timeslot(0)
            t1 = course.get_students_in_timeslot(1)
            t2 = course.get_students_in_timeslot(2)
            course_stats.append({
                'name': course_name,
                'total': total,
                'timeslot1': t0,
                'timeslot2': t1,
                'timeslot3': t2
            })
        
        course_stats.sort(key=lambda x: x['total'], reverse=True)
        avg_students = sum(c['total'] for c in course_stats) / len(course_stats) if course_stats else 0
        
        return jsonify({
            'success': True,
            'stats': {
                'studentCount': len(students),
                'courseCount': len(courses),
                'totalWishes': total_wishes,
                'fulfilledWishes': total_fulfilled,
                'fulfillmentRate': round(fulfillment_rate, 1),
                'wishPriorities': {str(k): v for k, v in fulfilled_wishes.items()},
                'wishesPerStudent': {str(k): v for k, v in wishes_per_student.items()},
                'studentsWithoutWishes': len(students_without_wishes),
                'averageCourseSize': round(avg_students, 1),
                'courseStats': course_stats  # Alle Kurse anzeigen
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/download/<filename>')
def download(filename):
    """Download generierter Dateien (CSV oder Excel)"""
    allowed_files = [
        'zuteilung_schueler.csv', 'zuteilung_kurse.csv', 
        'zuteilung_schueler.xlsx', 'zuteilung_kurse.xlsx',
        'zusammenfassung.txt'
    ]
    
    if filename not in allowed_files:
        return jsonify({'error': 'File not found'}), 404
    
    # Bestimme den richtigen Pfad basierend auf dem Modus
    download_dir = RESULTS_DIR if IS_RAM_ONLY_MODE else SCRIPT_DIR
    
    # Wenn Excel angefragt wird, konvertiere CSV zu Excel
    if filename.endswith('.xlsx'):
        csv_filename = filename.replace('.xlsx', '.csv')
        csv_path = os.path.join(download_dir, csv_filename)
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'File not generated yet'}), 404
        
        try:
            # Konvertiere CSV zu Excel
            df = pd.read_csv(csv_path, encoding='utf-8')
            
            # Erstelle Excel-Datei im Speicher
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Zuteilung')
                
                # Auto-size columns für bessere Lesbarkeit
                worksheet = writer.sheets['Zuteilung']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Max 50 Zeichen
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            excel_buffer.seek(0)
            
            return send_file(
                excel_buffer,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            return jsonify({'error': f'Excel conversion failed: {str(e)}'}), 500
    
    # Standard CSV/TXT Download
    file_path = os.path.join(download_dir, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not generated yet'}), 404
    
    return send_file(file_path, as_attachment=True)

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Löscht die temporären Daten aus dem RAM (nicht die persistenten Dateien)"""
    global delete_timer, delete_timestamp
    
    current_data['students'] = None
    current_data['courses'] = None
    current_data['filename'] = None
    current_data['upload_path'] = None
    
    # Stoppe Timer falls aktiv
    if delete_timer is not None:
        delete_timer.cancel()
        delete_timer = None
        delete_timestamp = None
    
    return jsonify({
        'success': True,
        'message': 'Daten wurden aus dem Speicher gelöscht (persistente Dateien bleiben erhalten)'
    })

@app.route('/api/delete-timestamp', methods=['GET'])
def get_delete_timestamp():
    """Gibt den Zeitstempel zurück, wann die Dateien gelöscht werden"""
    return jsonify({
        'deleteTimestamp': delete_timestamp,
        'autoDeleteMinutes': AUTO_DELETE_MINUTES,
        'ramOnlyMode': IS_RAM_ONLY_MODE
    })

def is_port_available(port):
    """Prüft ob ein Port verfügbar ist"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.bind(('0.0.0.0', port))
        sock.close()
        return True
    except (socket.error, OSError):
        return False

def find_available_port(min_port=5000, max_port=5999, max_attempts=50):
    """Findet einen verfügbaren zufälligen Port im angegebenen Bereich"""
    attempts = 0
    tried_ports = set()
    
    while attempts < max_attempts:
        port = random.randint(min_port, max_port)
        
        # Überspringe bereits getestete Ports
        if port in tried_ports:
            continue
        
        tried_ports.add(port)
        attempts += 1
        
        if is_port_available(port):
            return port
    
    # Fallback: Durchsuche alle Ports sequentiell
    for port in range(min_port, max_port + 1):
        if port not in tried_ports and is_port_available(port):
            return port
    
    # Wenn kein Port gefunden wurde, verwende einen vom System zugewiesenen Port
    return None

if __name__ == '__main__':
    print("="*80)
    print("🚀 Methodentag Kurszuteilung - Web Interface")
    print("="*80)
    print(f"\n🖥️  Betriebssystem: {platform.system()}")
    
    if IS_RAM_ONLY_MODE:
        print(f"\n🔒 DATENSCHUTZMODUS (RAM-Only):")
        print(f"   • Keine persistente Speicherung")
        print(f"   • Alle Daten nur im RAM")
        print(f"   • Dateien werden nach Server-Neustart gelöscht")
    else:
        print(f"\n💾 Datenspeicherung:")
        print(f"   • Uploads: {UPLOADS_DIR}")
        print(f"   • Ergebnisse: {RESULTS_DIR}")
        print(f"   • Nicht über Web-Interface zugänglich")
    
    # Finde verfügbaren Port
    port = find_available_port()
    
    if port is None:
        print("\n⚠️  Warnung: Kein freier Port im Bereich 5000-5999 gefunden!")
        print("   Verwende Port 0 (System wählt automatisch)")
        port = 0
    
    url = f"http://localhost:{port}"
    print(f"\n🌐 Server läuft auf: {url}")
    print("\n" + "="*80 + "\n")
    
    # Öffne Browser automatisch nach kurzer Verzögerung
    def open_browser():
        import time
        time.sleep(1.5)  # Warte bis Server bereit ist
        try:
            webbrowser.open(url)
            print(f"🌐 Browser geöffnet: {url}")
        except Exception as e:
            print(f"⚠️  Konnte Browser nicht öffnen: {e}")
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
