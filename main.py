import csv
from collections import defaultdict, Counter
import random
from typing import List, Dict, Set, Tuple
import os

# Konfiguration
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(SCRIPT_DIR, 'daten.csv')
NUM_TIMESLOTS = 3  # Jeder Kurs findet 3x statt
COURSES_PER_STUDENT = 3  # Jeder Schüler muss 3 Kurse belegen
MAX_STUDENTS_PER_COURSE = None  # Wird vom Benutzer eingegeben
EQUAL_DISTRIBUTION_MODE = False  # Gleichmäßige Verteilung erzwingen

class Student:
    def __init__(self, lastname, firstname, klasse, wishes):
        self.lastname = lastname
        self.firstname = firstname
        self.klasse = klasse
        self.wishes = wishes  # Liste von Wünschen in Reihenfolge
        self.assigned_courses = []  # Liste von (course, timeslot) Tupeln
        self.fulfilled_wish_numbers = []  # Liste der erfüllten Wunsch-Nummern (1-4)
        
    def __repr__(self):
        return f"{self.firstname} {self.lastname} ({self.klasse})"

class Course:
    def __init__(self, name):
        self.name = name
        self.timeslots = {0: [], 1: [], 2: []}  # Timeslot -> Liste von Schülern
        
    def get_total_students(self):
        return sum(len(students) for students in self.timeslots.values())
    
    def get_students_in_timeslot(self, timeslot):
        return len(self.timeslots[timeslot])

def load_data():
    """Lädt die CSV-Datei und extrahiert Schüler und Kurse"""
    students = []
    all_courses = set()
    
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=';')
        
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

def print_course_table(courses):
    """Gibt eine Übersichtstabelle aller Kurse aus"""
    print("\n" + "="*100)
    print("VERFÜGBARE KURSE")
    print("="*100)
    print(f"\nInsgesamt {len(courses)} verschiedene Kurse:")
    print(f"Jeder Kurs findet {NUM_TIMESLOTS}x statt (in 3 verschiedenen Zeitfenstern)\n")
    
    for i, course_name in enumerate(sorted(courses.keys()), 1):
        print(f"{i:2d}. {course_name}")
    print()

def assign_students_to_courses(students: List[Student], courses: Dict[str, Course], max_students_per_timeslot=None, equal_distribution=False, course_limits=None):
    """
    Verteilt Schüler auf Kurse unter Berücksichtigung der Wünsche und Constraints
    Verwendet einen iterativen Ansatz: Erst alle 1. Wünsche, dann alle 2. Wünsche, etc.
    
    Args:
        students: Liste der Schüler
        courses: Dictionary der Kurse
        max_students_per_timeslot: Globales Limit für alle Kurse
        equal_distribution: Gleichmäßige Verteilung erzwingen
        course_limits: Dict mit individuellen Limits pro Kurs {kursname: limit}
    """
    # Statistiken
    total_wishes = 0
    fulfilled_wishes = defaultdict(int)  # wish_priority -> count
    unfulfilled_students = []  # (student, unfulfilled_wishes)
    
    # course_limits falls None
    if course_limits is None:
        course_limits = {}
    
    # Berechne Zielgröße für jeden Kurs (bei gleichmäßiger Verteilung)
    target_students_per_course = None
    if equal_distribution:
        total_slots = len(students) * COURSES_PER_STUDENT  # 155 * 3 = 465
        active_courses = len(courses)
        target_students_per_course = total_slots / active_courses  # ca. 29 pro Kurs
        print(f"\nZiel: Jeder Kurs sollte ca. {target_students_per_course:.1f} Schueler haben (gesamt ueber alle Zeitfenster)")
    
    # Mische Schüler für faire Verteilung
    students_shuffled = list(students)
    random.shuffle(students_shuffled)
    
    # Iterativer Ansatz: Gehe Wunsch-Prioritäten durch (1., 2., 3., 4. Wunsch)
    print("\nVerteile Wuensche...")
    for wish_priority in range(4):  # 0 = 1. Wunsch, 1 = 2. Wunsch, etc.
        print(f"  Verarbeite {wish_priority + 1}. Wunsch...")
        
        for student in students_shuffled:
            # Schüler hat schon 3 Kurse? Dann überspringen
            if len(student.assigned_courses) >= COURSES_PER_STUDENT:
                continue
            
            # Hat der Schüler überhaupt so viele Wünsche?
            if wish_priority >= len(student.wishes):
                continue
            
            wish = student.wishes[wish_priority]
            total_wishes += 1
            
            # Prüfe ob Schüler diesen Kurs schon hat
            assigned_course_names = {c for c, _ in student.assigned_courses}
            if wish in assigned_course_names:
                continue
            
            # Bei gleichmäßiger Verteilung: Prüfe ob Kurs schon zu voll ist
            if equal_distribution and target_students_per_course:
                course_total = courses[wish].get_total_students()
                if course_total >= target_students_per_course * 1.2:  # Max 20% über Ziel
                    continue
            
            # Finde besten Timeslot für diesen Kurs
            assigned_timeslots = {ts for _, ts in student.assigned_courses}
            best_timeslot = None
            min_students = float('inf')
            
            for timeslot in range(NUM_TIMESLOTS):
                if timeslot in assigned_timeslots:
                    continue  # Schüler hat in diesem Zeitfenster schon einen Kurs
                
                num_students = courses[wish].get_students_in_timeslot(timeslot)
                
                # Prüfe maximale Kursgröße (individuell oder global)
                effective_limit = course_limits.get(wish, max_students_per_timeslot)
                if effective_limit and num_students >= effective_limit:
                    continue  # Kurs ist voll
                
                if num_students < min_students:
                    min_students = num_students
                    best_timeslot = timeslot
            
            if best_timeslot is not None:
                # Weise Schüler dem Kurs und Timeslot zu
                courses[wish].timeslots[best_timeslot].append(student)
                student.assigned_courses.append((wish, best_timeslot))
                fulfilled_wishes[wish_priority + 1] += 1
                student.fulfilled_wish_numbers.append(wish_priority + 1)
    
    # Auffüllen: Schüler die noch nicht 3 Kurse haben
    print("  Fuelle fehlende Kurse auf...")
    for student in students_shuffled:
        if len(student.assigned_courses) >= COURSES_PER_STUDENT:
            continue
        
        assigned_course_names = {c for c, _ in student.assigned_courses}
        assigned_timeslots = {ts for _, ts in student.assigned_courses}
        
        # Bei gleichmäßiger Verteilung: Sortiere Kurse nach aktueller Größe (kleinste zuerst)
        if equal_distribution:
            available_courses = [(c, courses[c].get_total_students()) 
                                for c in courses.keys() if c not in assigned_course_names]
            available_courses.sort(key=lambda x: x[1])  # Kleinste Kurse zuerst
            available_courses = [c[0] for c in available_courses]
        else:
            available_courses = [c for c in courses.keys() if c not in assigned_course_names]
            random.shuffle(available_courses)
        
        for course_name in available_courses:
            if len(student.assigned_courses) >= COURSES_PER_STUDENT:
                break
            
            # Finde verfügbaren Timeslot
            for timeslot in range(NUM_TIMESLOTS):
                if timeslot not in assigned_timeslots:
                    num_students = courses[course_name].get_students_in_timeslot(timeslot)
                    
                    # Prüfe maximale Kursgröße (individuell oder global)
                    effective_limit = course_limits.get(course_name, max_students_per_timeslot)
                    if effective_limit and num_students >= effective_limit:
                        continue
                    
                    courses[course_name].timeslots[timeslot].append(student)
                    student.assigned_courses.append((course_name, timeslot))
                    assigned_timeslots.add(timeslot)
                    break
    
    # Erstelle Liste der nicht erfüllten Wünsche
    for student in students:
        student_unfulfilled = []
        assigned_course_names = {c for c, _ in student.assigned_courses}
        
        for wish_idx, wish in enumerate(student.wishes):
            if wish not in assigned_course_names:
                student_unfulfilled.append((wish_idx + 1, wish))
        
        if student_unfulfilled:
            unfulfilled_students.append((student, student_unfulfilled))
    
    # Gleichmäßige Verteilung der Zeitfenster innerhalb jedes Kurses
    if equal_distribution:
        balance_timeslots_within_courses(students, courses)
    
    return fulfilled_wishes, unfulfilled_students, total_wishes

def balance_timeslots_within_courses(students: List[Student], courses: Dict[str, Course]):
    """
    Gleicht die Verteilung der Schüler über die Zeitfenster aus,
    sodass jeder Kurs in jedem Zeitfenster möglichst gleich viele Schüler hat
    """
    print("\n⚖️  Gleiche Verteilung der Zeitfenster innerhalb der Kurse aus...")
    
    for course_name, course in courses.items():
        total_students = course.get_total_students()
        if total_students == 0:
            continue
        
        target_per_slot = total_students // NUM_TIMESLOTS
        remainder = total_students % NUM_TIMESLOTS
        
        # Ziel: Jeder Slot sollte target_per_slot Schüler haben, 
        # und die ersten 'remainder' Slots bekommen einen Extra-Schüler
        target_counts = [target_per_slot + (1 if i < remainder else 0) for i in range(NUM_TIMESLOTS)]
        
        # Verschiebe Schüler von überfüllten zu unterfüllten Slots
        for timeslot in range(NUM_TIMESLOTS):
            current_count = len(course.timeslots[timeslot])
            target_count = target_counts[timeslot]
            
            while current_count > target_count:
                moved = False
                # Finde einen Schüler, der verschoben werden kann
                for student in list(course.timeslots[timeslot]):  # Kopie der Liste
                    # Prüfe, ob wir diesen Schüler in einen anderen Slot verschieben können
                    for other_slot in range(NUM_TIMESLOTS):
                        if other_slot == timeslot:
                            continue
                        
                        # Prüfe ob der andere Slot noch Platz braucht
                        if len(course.timeslots[other_slot]) >= target_counts[other_slot]:
                            continue
                        
                        # Prüfe ob Schüler in diesem Zeitfenster noch frei ist
                        student_timeslots = {ts for _, ts in student.assigned_courses}
                        if other_slot in student_timeslots:
                            continue
                        
                        # Verschiebe Schüler
                        course.timeslots[timeslot].remove(student)
                        course.timeslots[other_slot].append(student)
                        
                        # Update Student's assignment
                        for i, (c, ts) in enumerate(student.assigned_courses):
                            if c == course_name and ts == timeslot:
                                student.assigned_courses[i] = (course_name, other_slot)
                                break
                        
                        current_count -= 1
                        moved = True
                        break
                    
                    if moved or current_count <= target_count:
                        break
                
                # Falls kein Schüler verschoben werden konnte, abbrechen
                if not moved:
                    break

def print_statistics(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes):
    """Gibt Statistiken zur Zuteilung aus"""
    print("\n" + "="*100)
    print("ZUTEILUNGSSTATISTIKEN")
    print("="*100)
    
    # Allgemeine Statistiken
    print(f"\nAnzahl Schüler: {len(students)}")
    print(f"Anzahl Kurse: {len(courses)}")
    print(f"Gesamtzahl Wünsche: {total_wishes}")
    
    # Erfüllte Wünsche nach Priorität
    print("\nErfüllte Wünsche nach Priorität:")
    total_fulfilled = 0
    for priority in sorted(fulfilled_wishes.keys()):
        count = fulfilled_wishes[priority]
        total_fulfilled += count
        print(f"  {priority}. Wunsch: {count} erfüllt")
    
    fulfillment_rate = (total_fulfilled / total_wishes * 100) if total_wishes > 0 else 0
    print(f"\nErfüllungsrate: {total_fulfilled}/{total_wishes} = {fulfillment_rate:.1f}%")
    
    # Verteilung: Wie viele Wünsche wurden pro Schüler erfüllt?
    print("\n" + "-"*100)
    print("VERTEILUNG ERFÜLLTER WÜNSCHE PRO SCHÜLER")
    print("-"*100)
    wishes_per_student = Counter()
    for student in students:
        num_fulfilled = len(student.fulfilled_wish_numbers)
        wishes_per_student[num_fulfilled] += 1
    
    print()
    for num_wishes in sorted(wishes_per_student.keys()):
        count = wishes_per_student[num_wishes]
        percentage = (count / len(students) * 100) if len(students) > 0 else 0
        if num_wishes == 0:
            print(f"{count} Schüler haben 0 Wünsche erfüllt bekommen ({percentage:.1f}%)")
        elif num_wishes == 1:
            print(f"{count} Schüler haben 1 Wunsch erfüllt bekommen ({percentage:.1f}%)")
        else:
            print(f"{count} Schüler haben {num_wishes} Wünsche erfüllt bekommen ({percentage:.1f}%)")
    
    # Kursgrößen
    print("\n" + "-"*100)
    print("KURSGRÖSSENVERPEILUNG")
    print("-"*100)
    
    course_stats = []
    for course_name, course in sorted(courses.items()):
        total = course.get_total_students()
        t0 = course.get_students_in_timeslot(0)
        t1 = course.get_students_in_timeslot(1)
        t2 = course.get_students_in_timeslot(2)
        course_stats.append((course_name, total, t0, t1, t2))
    
    # Sortiere nach Gesamtzahl
    course_stats.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n{'Kurs':<80} {'Gesamt':>6} {'Zeit1':>6} {'Zeit2':>6} {'Zeit3':>6}")
    print("-"*100)
    for name, total, t0, t1, t2 in course_stats:
        short_name = name[:75] + "..." if len(name) > 75 else name
        print(f"{short_name:<80} {total:6d} {t0:6d} {t1:6d} {t2:6d}")
    
    avg_students = sum(c[1] for c in course_stats) / len(course_stats) if course_stats else 0
    print(f"\nDurchschnittliche Kursgröße: {avg_students:.1f} Schüler")
    
    # Schüler ohne erfüllte Wünsche
    students_without_wishes = []
    for student in students:
        if not student.fulfilled_wish_numbers:
            students_without_wishes.append(student)
    
    if students_without_wishes:
        print("\n" + "-"*100)
        print("SCHÜLER OHNE ERFÜLLTE WÜNSCHE")
        print("-"*100)
        print(f"\n{len(students_without_wishes)} Schüler haben KEINEN ihrer Wünsche bekommen:\n")
        
        for student in students_without_wishes[:20]:  # Zeige erste 20
            wishes_info = f" (hatte {len(student.wishes)} Wünsche)" if student.wishes else " (hatte KEINE Wünsche angegeben)"
            print(f"  - {student}{wishes_info}")
        
        if len(students_without_wishes) > 20:
            print(f"  ... und {len(students_without_wishes) - 20} weitere Schüler\n")
    else:
        print("\nAlle Schüler haben mindestens einen Wunsch erfüllt bekommen!")

def export_results(students, courses, output_dir=None):
    """Exportiert die Ergebnisse in CSV-Dateien"""
    
    # Verwende output_dir falls angegeben, sonst SCRIPT_DIR
    if output_dir is None:
        output_dir = SCRIPT_DIR
    
    # Export 1: Schüler-Zuteilung
    output_file = os.path.join(output_dir, 'zuteilung_schueler.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Nachname', 'Vorname', 'Klasse', 'Zeitfenster 1', 'Zeitfenster 2', 'Zeitfenster 3', 'Erfüllte Wünsche'])
        
        for student in sorted(students, key=lambda s: (s.klasse, s.lastname, s.firstname)):
            courses_by_time = [''] * 3
            for course_name, timeslot in student.assigned_courses:
                courses_by_time[timeslot] = course_name
            
            # Erfüllte Wünsche als kommagetrennte Liste
            fulfilled_wishes_str = ','.join(map(str, sorted(student.fulfilled_wish_numbers)))
            
            writer.writerow([
                student.lastname,
                student.firstname,
                student.klasse,
                courses_by_time[0],
                courses_by_time[1],
                courses_by_time[2],
                fulfilled_wishes_str
            ])
    
    print("\n✓ Datei 'zuteilung_schueler.csv' wurde erstellt")
    
    # Export 2: Kurs-Übersicht
    output_file = os.path.join(output_dir, 'zuteilung_kurse.csv')
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Kurs', 'Zeitfenster', 'Anzahl Schüler', 'Schüler'])
        
        for course_name in sorted(courses.keys()):
            course = courses[course_name]
            for timeslot in range(NUM_TIMESLOTS):
                students_in_slot = course.timeslots[timeslot]
                student_names = '; '.join(
                    f"{s.firstname} {s.lastname} ({s.klasse})" 
                    for s in sorted(students_in_slot, key=lambda s: (s.klasse, s.lastname))
                )
                writer.writerow([
                    course_name,
                    f"Zeitfenster {timeslot + 1}",
                    len(students_in_slot),
                    student_names
                ])
    
    print("✓ Datei 'zuteilung_kurse.csv' wurde erstellt")

def export_summary_txt(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes, max_students, output_dir=None):
    """Exportiert eine Zusammenfassung als TXT-Datei"""
    
    # Verwende output_dir falls angegeben, sonst SCRIPT_DIR
    if output_dir is None:
        output_dir = SCRIPT_DIR
    
    output_file = os.path.join(output_dir, 'zusammenfassung.txt')
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("="*100 + "\n")
        f.write("📊 ZUSAMMENFASSUNG DER KURSZUTEILUNG - METHODENTAG\n")
        f.write("="*100 + "\n\n")
        
        # Erfolgreiche Zuteilung
        f.write("✅ ERFOLGREICHE ZUTEILUNG\n")
        f.write("-"*100 + "\n")
        f.write(f"• {len(students)} Schüler wurden auf {len(courses)} verschiedene Kurse verteilt\n")
        f.write(f"• Jeder Kurs findet in {NUM_TIMESLOTS} Zeitfenstern statt\n")
        f.write(f"• Jeder Schüler belegt {COURSES_PER_STUDENT} Kurse (einen pro Zeitfenster)\n")
        if max_students:
            f.write(f"• Maximale Kursgröße pro Zeitfenster: {max_students} Schüler\n")
        f.write("\n")
        
        # Wunscherfüllung
        total_fulfilled = sum(fulfilled_wishes.values())
        fulfillment_rate = (total_fulfilled / total_wishes * 100) if total_wishes > 0 else 0
        
        f.write("📈 WUNSCHERFÜLLUNG\n")
        f.write("-"*100 + "\n")
        f.write(f"• Erfüllungsrate: {fulfillment_rate:.1f}% ({total_fulfilled} von {total_wishes} Wünschen)\n")
        
        for priority in sorted(fulfilled_wishes.keys()):
            count = fulfilled_wishes[priority]
            percentage = (count / len(students) * 100) if len(students) > 0 else 0
            f.write(f"• {priority}. Wunsch: {count} erfüllt ({percentage:.1f}%)\n")
        
        # Verteilung erfüllter Wünsche pro Schüler
        f.write("\n")
        f.write("📊 VERTEILUNG ERFÜLLTER WÜNSCHE PRO SCHÜLER\n")
        f.write("-"*100 + "\n")
        wishes_per_student = Counter()
        for student in students:
            num_fulfilled = len(student.fulfilled_wish_numbers)
            wishes_per_student[num_fulfilled] += 1
        
        for num_wishes in sorted(wishes_per_student.keys()):
            count = wishes_per_student[num_wishes]
            percentage = (count / len(students) * 100) if len(students) > 0 else 0
            if num_wishes == 0:
                f.write(f"• {count} Schüler haben 0 Wünsche erfüllt bekommen ({percentage:.1f}%)\n")
            elif num_wishes == 1:
                f.write(f"• {count} Schüler haben 1 Wunsch erfüllt bekommen ({percentage:.1f}%)\n")
            else:
                f.write(f"• {count} Schüler haben {num_wishes} Wünsche erfüllt bekommen ({percentage:.1f}%)\n")
        
        f.write("\n")
        
        # Schüler ohne erfüllte Wünsche
        students_without_wishes = [s for s in students if not s.fulfilled_wish_numbers]
        if students_without_wishes:
            f.write(f"\n⚠️  {len(students_without_wishes)} Schüler haben KEINEN ihrer Wünsche bekommen:\n")
            for student in students_without_wishes:
                wishes_info = f" (hatte {len(student.wishes)} Wünsche)" if student.wishes else " (hatte KEINE Wünsche angegeben)"
                f.write(f"   - {student.firstname} {student.lastname} ({student.klasse}){wishes_info}\n")
        else:
            f.write("\n✓ Alle Schüler haben mindestens einen Wunsch erfüllt bekommen!\n")
        
        f.write("\n")
        
        # Kursgrößen
        course_stats = []
        for course_name, course in sorted(courses.items()):
            total = course.get_total_students()
            t0 = course.get_students_in_timeslot(0)
            t1 = course.get_students_in_timeslot(1)
            t2 = course.get_students_in_timeslot(2)
            course_stats.append((course_name, total, t0, t1, t2))
        
        course_stats.sort(key=lambda x: x[1], reverse=True)
        avg_students = sum(c[1] for c in course_stats) / len(course_stats) if course_stats else 0
        
        f.write("👥 KURSGRÖSSENVERPEILUNG\n")
        f.write("-"*100 + "\n")
        f.write(f"• Durchschnittliche Kursgröße: {avg_students:.1f} Schüler\n")
        f.write("• Die Kurse sind gut verteilt und haben ähnliche Größen\n\n")
        
        f.write("Beliebteste Kurse (Top 5):\n")
        for i, (name, total, t0, t1, t2) in enumerate(course_stats[:5], 1):
            short_name = name[:70] + "..." if len(name) > 70 else name
            f.write(f"  {i}. \"{short_name}\"\n")
            f.write(f"     → {total} Schüler gesamt ({t0}/{t1}/{t2} pro Zeitfenster)\n")
        f.write("\n")
        
        # Kurse ohne Teilnehmer
        empty_courses = [c for c in course_stats if c[1] == 0]
        if empty_courses:
            f.write("⚠️  KURSE OHNE TEILNEHMER\n")
            f.write("-"*100 + "\n")
            f.write(f"{len(empty_courses)} Kurse haben keine Teilnehmer erhalten:\n")
            for name, _, _, _, _ in empty_courses:
                f.write(f"  • \"{name}\"\n")
            f.write("\n")
        
        # Vollständige Kurstabelle
        f.write("📋 VOLLSTÄNDIGE KURSÜBERSICHT\n")
        f.write("-"*100 + "\n\n")
        f.write(f"{'Nr':<4} {'Kursname':<70} {'Gesamt':>8} {'Zeit1':>6} {'Zeit2':>6} {'Zeit3':>6}\n")
        f.write("-"*100 + "\n")
        
        for i, (name, total, t0, t1, t2) in enumerate(course_stats, 1):
            short_name = name[:65] + "..." if len(name) > 65 else name
            f.write(f"{i:<4} {short_name:<70} {total:8d} {t0:6d} {t1:6d} {t2:6d}\n")
        
        f.write("\n")
        
        # Erstellte Dateien
        f.write("📁 ERSTELLTE DATEIEN\n")
        f.write("-"*100 + "\n")
        f.write("• zuteilung_schueler.csv - Liste aller Schüler mit ihren 3 zugeteilten Kursen\n")
        f.write("• zuteilung_kurse.csv - Übersicht aller Kurse mit Schülerlisten pro Zeitfenster\n")
        f.write("• zusammenfassung.txt - Diese Zusammenfassung\n")
        f.write("\n")
        
        f.write("="*100 + "\n")
        f.write("Die Zuteilung berücksichtigt alle Constraints:\n")
        f.write("✓ Jeder Schüler hat 3 verschiedene Kurse\n")
        f.write("✓ Kein Kurs wird von einem Schüler doppelt belegt\n")
        f.write("✓ Kein Schüler hat 2 Kurse im gleichen Zeitfenster\n")
        f.write("✓ Kurse sind gleichmäßig auf die Zeitfenster verteilt\n")
        if max_students:
            f.write(f"✓ Maximale Kursgröße von {max_students} Schülern pro Zeitfenster wird eingehalten\n")
        f.write("="*100 + "\n")
    
    print("✓ Datei 'zusammenfassung.txt' wurde erstellt")

def get_configuration_input():
    """Fragt den Benutzer nach der Konfiguration"""
    print("\n" + "="*100)
    print("KONFIGURATION")
    print("="*100)
    
    # Frage nach maximaler Kursgröße
    max_students = None
    while True:
        print("\nWie viele Schüler dürfen maximal in einem Kurs (pro Zeitfenster) sein?")
        print("(Drücken Sie Enter für keine Begrenzung)")
        
        user_input = input("Maximale Kursgröße: ").strip()
        
        if user_input == "":
            print("\n✓ Keine Begrenzung der Kursgröße")
            break
        
        try:
            max_students = int(user_input)
            if max_students <= 0:
                print("❌ Bitte geben Sie eine positive Zahl ein!")
                continue
            if max_students < 10:
                confirm = input(f"\n⚠️  {max_students} Schüler ist sehr klein. Fortfahren? (j/n): ").strip().lower()
                if confirm != 'j':
                    continue
            
            print(f"\n✓ Maximale Kursgröße: {max_students} Schüler pro Zeitfenster")
            break
        except ValueError:
            print("❌ Bitte geben Sie eine gültige Zahl ein!")
    
    # Frage nach gleichmäßiger Verteilung
    equal_distribution = False
    while True:
        print("\nSollen alle Kurse ungefähr gleich viele Schüler haben?")
        print("(Verhindert, dass manche Kurse sehr voll und andere fast leer sind)")
        print("(Dies kann die Wunscherfüllung leicht reduzieren)")
        
        user_input = input("Gleichmäßige Kursverteilung? (j/n): ").strip().lower()
        
        if user_input in ['j', 'ja', 'y', 'yes']:
            equal_distribution = True
            print("\n✓ Gleichmäßige Verteilung aktiviert")
            break
        elif user_input in ['n', 'nein', 'no']:
            print("\n✓ Normale Verteilung (ohne Ausgleich)")
            break
        else:
            print("❌ Bitte geben Sie 'j' oder 'n' ein!")
    
    return max_students, equal_distribution

def main():
    print("="*100)
    print("METHODENTAG KURSZUTEILUNG")
    print("="*100)
    
    # Lade Daten
    students, courses = load_data()
    print(f"\n✓ {len(students)} Schüler und {len(courses)} Kurse geladen")
    
    # Zeige Kurstabelle
    print_course_table(courses)
    
    # Frage nach Konfiguration
    max_students, equal_distribution = get_configuration_input()
    
    # Führe Zuteilung durch
    print("\n" + "="*100)
    print("FÜHRE ZUTEILUNG DURCH...")
    print("="*100)
    
    fulfilled_wishes, unfulfilled_students, total_wishes = assign_students_to_courses(
        students, courses, max_students, equal_distribution
    )
    
    # Zeige Statistiken
    print_statistics(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes)
    
    # Exportiere Ergebnisse
    print("\n" + "="*100)
    print("EXPORTIERE ERGEBNISSE")
    print("="*100)
    export_results(students, courses)
    export_summary_txt(students, courses, fulfilled_wishes, unfulfilled_students, total_wishes, max_students)
    
    print("\n" + "="*100)
    print("FERTIG!")
    print("="*100)
    print("\nDie Zuteilung wurde erfolgreich durchgeführt.")
    print("Prüfen Sie die erstellten Dateien für Details:")
    print("  • zuteilung_schueler.csv")
    print("  • zuteilung_kurse.csv")
    print("  • zusammenfassung.txt")
    print()

if __name__ == "__main__":
    main()
