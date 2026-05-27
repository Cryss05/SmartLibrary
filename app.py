from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "smart_library_secret_key_for_session" # Cheie secreta pentru sesiuni securizate

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configurare folder pentru copertile incarcate
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    """Creeaza o conexiune la baza de date SQLite cu cheile externe activate."""
    conn = sqlite3.connect(os.path.join(BASE_DIR, "library.db"))
    conn.row_factory = sqlite3.Row  # Ne permite sa accesam coloanele dupa nume (ex: row['title'])
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def clean_expired_reservations():
    """Identifica rezervarile pending care au depasit 48h, le anuleaza si returneaza cartile in stoc."""
    conn = get_db_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Gasim rezervarile pending expirate
        expired = cursor.execute(
            "SELECT id, book_id FROM reservations WHERE status = 'pending' AND expires_at < ?",
            (now_str,)
        ).fetchall()
        
        if expired:
            for res in expired:
                cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (res[0],))
                cursor.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (res[1],))
            conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
    finally:
        conn.close()

@app.before_request
def check_valid_session():
    """Valideaza daca utilizatorul din sesiune mai exista in baza de date (de ex. dupa resetare db)."""
    # Excludem verificarea pentru fisierele statice pentru a evita interogari inutile ale bazei de date
    if request.endpoint == 'static':
        return
        
    if "user_id" in session:
        conn = get_db_connection()
        user = conn.execute("SELECT id FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
        if not user:
            session.clear()

@app.context_processor
def inject_user():
    """Injecteaza datele utilizatorului logat in toate template-urile HTML."""
    user = None
    if "user_id" in session:
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
        conn.close()
    return dict(current_user=user)

# Filtru Jinja2 pentru formatarea datelor in format romanesc
LUNI_RO = [
    "Ianuarie", "Februarie", "Martie", "Aprilie", "Mai", "Iunie",
    "Iulie", "August", "Septembrie", "Octombrie", "Noiembrie", "Decembrie"
]

@app.template_filter('format_date')
def format_date(value):
    """Converteste un timestamp SQL (YYYY-MM-DD HH:MM:SS) in format romanesc (27 Mai 2026, 17:43)."""
    if not value:
        return "-"
    try:
        if isinstance(value, str):
            dt = datetime.strptime(value[:16], "%Y-%m-%d %H:%M")
        else:
            dt = value
        return f"{dt.day} {LUNI_RO[dt.month - 1]} {dt.year}, {dt.strftime('%H:%M')}"
    except (ValueError, TypeError):
        return value

# ==========================================
# Rute Principale & Cautare
# ==========================================

@app.route("/")
def index():
    """Afiseaza catalogul de carti cu posibilitate de cautare."""
    clean_expired_reservations()
    conn = get_db_connection()
    
    # Selectam toate cartile pentru a permite filtrarea in timp real in JS
    books = conn.execute("SELECT * FROM books").fetchall()
    
    # Selectam categoriile unice pentru filtrare
    categories = [row["category"] for row in conn.execute("SELECT DISTINCT category FROM books ORDER BY category ASC").fetchall()]
    
    # Selectam autorii unici pentru auto-suggestion
    authors = [row["author"] for row in conn.execute("SELECT DISTINCT author FROM books ORDER BY author ASC").fetchall()]
    
    # Selectam titlurile unice pentru auto-suggestion
    titles = [row["title"] for row in conn.execute("SELECT DISTINCT title FROM books ORDER BY title ASC").fetchall()]
    
    conn.close()
    
    return render_template("index.html", books=books, categories=categories, authors=authors, titles=titles)

@app.route("/book/<int:book_id>")
def book_details(book_id):
    """Afiseaza detaliile unei carti specifice."""
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    conn.close()
    
    if not book:
        flash("Cartea nu a fost găsită!", "danger")
        return redirect(url_for("index"))
        
    return render_template("book_details.html", book=book)

# ==========================================
# Rute de Autentificare (Autentificare/Inregistrare)
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():
    """Inregistreaza un utilizator nou (UC1)."""
    if "user_id" in session:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("Toate câmpurile sunt obligatorii!", "warning")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Parolele introduse nu coincid! Te rugăm să verifici.", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        # Verificam daca email-ul exista deja (SQL Query)
        existing_user = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        
        if existing_user:
            flash("Adresa de email este deja înregistrată!", "danger")
            conn.close()
            return redirect(url_for("register"))
            
        # Inseram noul utilizator (SQL Query)
        try:
            hashed_pw = generate_password_hash(password)
            conn.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'cititor')",
                (name, email, hashed_pw)
            )
            conn.commit()
            flash("Te-ai înregistrat cu succes! Te poți autentifica acum.", "success")
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.Error as e:
            flash(f"Eroare la înregistrare: {e}", "danger")
            conn.close()
            
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Autentifica un utilizator (UC2)."""
    if "user_id" in session:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        
        conn = get_db_connection()
        # Cautam utilizatorul dupa email (SQL Query)
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        # Verificam parola criptata
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]
            flash(f"Bine ai revenit, {user['name']}!", "success")
            return redirect(url_for("index"))
        else:
            flash("Email sau parolă incorectă!", "danger")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    """Delogheaza utilizatorul (UC3)."""
    session.clear()
    flash("Te-ai delogat cu succes.", "info")
    return redirect(url_for("index"))

# ==========================================
# Rute pentru Rezervari
# ==========================================

@app.route("/reserve/<int:book_id>", methods=["POST"])
def reserve_book(book_id):
    """Creeaza o rezervare pentru o carte (UC6)."""
    if "user_id" not in session:
        flash("Trebuie să fii autentificat pentru a rezerva o carte!", "warning")
        return redirect(url_for("login"))
        
    conn = get_db_connection()
    # 1. Verificam disponibilitatea cartii
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    
    if not book:
        flash("Cartea nu există!", "danger")
        conn.close()
        return redirect(url_for("index"))
        
    if book["available_copies"] <= 0:
        flash("Ne pare rău, nu mai sunt exemplare disponibile pentru această carte!", "danger")
        conn.close()
        return redirect(url_for("index"))
        
    # 2. Verificam daca utilizatorul are deja o rezervare activa sau un imprumut activ pentru aceasta carte
    existing_reservation = conn.execute(
        "SELECT id FROM reservations WHERE user_id = ? AND book_id = ? AND status IN ('pending', 'borrowed')",
        (session["user_id"], book_id)
    ).fetchone()
    
    if existing_reservation:
        flash("Ai deja o rezervare sau un împrumut activ pentru această carte!", "warning")
        conn.close()
        return redirect(url_for("index"))
        
    # 3. Cream rezervarea (pending pickup) si scadem stocul disponibil (Tranzactie SQL)
    try:
        now = datetime.now()
        expires = now + timedelta(days=2) # Rezervare valabila 48 de ore pentru ridicare
        
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        expires_str = expires.strftime("%Y-%m-%d %H:%M:%S")
        
        # Adaugare rezervare in starea 'pending'
        conn.execute(
            "INSERT INTO reservations (user_id, book_id, status, reserved_at, expires_at) VALUES (?, ?, 'pending', ?, ?)",
            (session["user_id"], book_id, now_str, expires_str)
        )
        # Modificare numar exemplare disponibile
        conn.execute(
            "UPDATE books SET available_copies = available_copies - 1 WHERE id = ?",
            (book_id,)
        )
        
        conn.commit()
        flash(f"Rezervarea pentru '{book['title']}' a fost realizată! Te rugăm să o ridici în termen de 48 de ore.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare la rezervare: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))

@app.route("/cancel-reservation/<int:res_id>", methods=["POST"])
def cancel_reservation(res_id):
    """Anuleaza o rezervare in curs de ridicare (UC7)."""
    if "user_id" not in session:
        return redirect(url_for("login"))
        
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    
    if not res:
        flash("Rezervarea nu a fost găsită!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    # Validam permisiunea
    if res["user_id"] != session["user_id"] and session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Nu ai permisiunea de a anula această rezervare!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    if res["status"] != "pending":
        flash("Doar rezervările aflate în așteptarea ridicării pot fi anulate!", "warning")
        conn.close()
        return redirect(url_for("dashboard"))
        
    # Anulam rezervarea si returnam cartea in stoc
    try:
        conn.execute("UPDATE reservations SET status = 'cancelled' WHERE id = ?", (res_id,))
        conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (res["book_id"],))
        conn.commit()
        flash("Rezervarea a fost anulată cu succes.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare la anulare: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))

# ==========================================
# Rute de Administrare (Dashboard Utilizatori / Staff)
# ==========================================

@app.route("/dashboard")
def dashboard():
    """Afiseaza pagina de profil cu rezervari (UC8) sau panoul de gestiune (UC9, UC10, UC11)."""
    clean_expired_reservations()
    if "user_id" not in session:
        flash("Trebuie să fii autentificat pentru a accesa panoul!", "warning")
        return redirect(url_for("login"))
        
    conn = get_db_connection()
    role = session["user_role"]
    
    if role == "cititor":
        # Pentru cititori, afisam doar rezervarile proprii cu JOIN pentru detalii carte
        reservations = conn.execute(
            """
            SELECT r.id, r.status, r.reserved_at, r.expires_at, r.borrowed_at, r.return_deadline, b.title, b.author, b.id as book_id
            FROM reservations r
            JOIN books b ON r.book_id = b.id
            WHERE r.user_id = ?
            ORDER BY r.reserved_at DESC;
            """,
            (session["user_id"],)
        ).fetchall()
        conn.close()
        return render_template("dashboard_reader.html", reservations=reservations)
        
    elif role == "admin":
        # Pentru admin: afisam panoul de gestionare utilizatori
        users = conn.execute("SELECT id, name, email, role, created_at FROM users ORDER BY role ASC, name ASC").fetchall()
        conn.close()
        return render_template("dashboard_admin.html", users=users)

    elif role == "bibliotecar":
        # Pentru bibliotecari, afisam toate cartile si toate rezervarile din sistem
        books = conn.execute("SELECT * FROM books ORDER BY title ASC").fetchall()
        reservations = conn.execute(
            """
            SELECT r.id, r.status, r.reserved_at, r.expires_at, r.borrowed_at, r.return_deadline, b.title, u.name as user_name, u.email as user_email
            FROM reservations r
            JOIN books b ON r.book_id = b.id
            JOIN users u ON r.user_id = u.id
            ORDER BY r.reserved_at DESC;
            """
        ).fetchall()
        conn.close()
        return render_template("dashboard_staff.html", books=books, reservations=reservations)

# ==========================================
# Rute de Gestiune Carti (Librarian/Admin) (UC9, UC10, UC11)
# ==========================================

@app.route("/admin/book/add", methods=["POST"])
def admin_add_book():
    """Adauga o carte noua in sistem (UC9)."""
    if "user_id" not in session or session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))
        
    title = request.form["title"].strip()
    author = request.form["author"].strip()
    category = request.form["category"].strip()
    description = request.form["description"].strip()
    copies = int(request.form["total_copies"])
    
    # Procesare incarcare fisier imagine coperta
    cover_url = ""
    if 'cover_file' in request.files:
        file = request.files['cover_file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_url = f"/static/uploads/{filename}"
            
    # Daca nu s-a incarcat un fisier, verificam daca s-a trimis un URL text (optional)
    if not cover_url:
        cover_url = request.form.get("cover_url", "").strip()
        
    if not title or not author or not category or copies < 1:
        flash("Date invalide pentru introducerea cărții!", "warning")
        return redirect(url_for("dashboard"))
        
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO books (title, author, category, description, cover_url, total_copies, available_copies)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (title, author, category, description, cover_url, copies, copies)
        )
        conn.commit()
        flash(f"Cartea '{title}' a fost adăugată cu succes în catalog!", "success")
    except sqlite3.Error as e:
        flash(f"Eroare SQL: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))

@app.route("/admin/book/edit/<int:book_id>", methods=["POST"])
def admin_edit_book(book_id):
    """Modifica informatiile unei carti (UC10)."""
    if "user_id" not in session or session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))
        
    title = request.form["title"].strip()
    author = request.form["author"].strip()
    category = request.form["category"].strip()
    description = request.form["description"].strip()
    total_copies = int(request.form["total_copies"])
    
    conn = get_db_connection()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    
    if not book:
        flash("Cartea nu a fost găsită!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    # Procesare incarcare fisier imagine coperta pentru editare
    cover_url = ""
    if 'cover_file' in request.files:
        file = request.files['cover_file']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cover_url = f"/static/uploads/{filename}"
            
    # Daca nu s-a incarcat un fisier nou, verificam daca s-a completat un URL text
    if not cover_url:
        cover_url = request.form.get("cover_url", "").strip()
        
    # Daca ambele sunt goale, pastram vechea coperta din baza de date
    if not cover_url:
        cover_url = book["cover_url"]
        
    # Calculam noile copii disponibile in functie de modificarea exemplarelor totale
    diff = total_copies - book["total_copies"]
    new_available = book["available_copies"] + diff
    
    if new_available < 0:
        flash("Nu poți reduce numărul total de exemplare sub numărul de cărți deja rezervate în acest moment!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    try:
        conn.execute(
            """
            UPDATE books 
            SET title = ?, author = ?, category = ?, description = ?, cover_url = ?, total_copies = ?, available_copies = ?
            WHERE id = ?;
            """,
            (title, author, category, description, cover_url, total_copies, new_available, book_id)
        )
        conn.commit()
        flash(f"Cartea '{title}' a fost modificată cu succes!", "success")
    except sqlite3.Error as e:
        flash(f"Eroare SQL: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))

@app.route("/admin/book/delete/<int:book_id>", methods=["POST"])
def admin_delete_book(book_id):
    """Sterge o carte din sistem (UC11)."""
    if "user_id" not in session or session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))
        
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        flash("Cartea a fost ștearsă din catalog cu succes!", "success")
    except sqlite3.Error as e:
        flash(f"Eroare la ștergerea cărții (este posibil să aibă rezervări active): {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))


@app.route("/admin/reservation/pickup/<int:res_id>", methods=["POST"])
def admin_pickup_book(res_id):
    """Confirma ridicarea fizica a cartii de catre cititor."""
    if "user_id" not in session or session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))
        
    days = int(request.form.get("days", 14)) # Implicit 14 zile
    if days < 1:
        flash("Numărul de zile de împrumut trebuie să fie de cel puțin 1 zi!", "warning")
        return redirect(url_for("dashboard"))
        
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    
    if not res:
        flash("Rezervarea nu există!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    if res["status"] != "pending":
        flash("Doar rezervările în așteptare pot fi ridicate!", "warning")
        conn.close()
        return redirect(url_for("dashboard"))
        
    try:
        now = datetime.now()
        deadline = now + timedelta(days=days)
        
        now_str = now.strftime("%Y-%m-%d %H:%M:%S")
        deadline_str = deadline.strftime("%Y-%m-%d %H:%M:%S")
        
        # Actualizam statusul la 'borrowed'
        conn.execute(
            """
            UPDATE reservations 
            SET status = 'borrowed', borrowed_at = ?, return_deadline = ? 
            WHERE id = ?;
            """,
            (now_str, deadline_str, res_id)
        )
        conn.commit()
        flash("Ridicarea cărții a fost confirmată! Împrumutul este acum activ.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare SQL: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))

@app.route("/admin/reservation/return/<int:res_id>", methods=["POST"])
def admin_return_book(res_id):
    """Marcheaza o carte ca returnata la raft."""
    if "user_id" not in session or session["user_role"] not in ["bibliotecar", "admin"]:
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))
        
    conn = get_db_connection()
    res = conn.execute("SELECT * FROM reservations WHERE id = ?", (res_id,)).fetchone()
    
    if not res:
        flash("Împrumutul nu există!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))
        
    if res["status"] != "borrowed":
        flash("Doar cărțile ridicate/împrumutate pot fi returnate!", "warning")
        conn.close()
        return redirect(url_for("dashboard"))
        
    try:
        # Marcam ca returnata
        conn.execute("UPDATE reservations SET status = 'returned' WHERE id = ?", (res_id,))
        # Adaugam copia inapoi in stoc
        conn.execute("UPDATE books SET available_copies = available_copies + 1 WHERE id = ?", (res["book_id"],))
        conn.commit()
        flash("Cartea a fost returnată la raft cu succes, iar exemplarul este din nou disponibil.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare: {e}", "danger")
    finally:
        conn.close()
        
    return redirect(url_for("dashboard"))


# ==========================================
# Rute de Administrare Utilizatori (Admin only)
# ==========================================

@app.route("/admin/user/create-librarian", methods=["POST"])
def admin_create_librarian():
    """Creeaza un cont de bibliotecar (doar Admin)."""
    if "user_id" not in session or session["user_role"] != "admin":
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not email or not password:
        flash("Toate campurile sunt obligatorii!", "warning")
        return redirect(url_for("dashboard"))

    if len(password) < 6:
        flash("Parola trebuie sa aiba cel putin 6 caractere!", "warning")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        flash(f"Adresa de email '{email}' este deja inregistrata in sistem!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))

    try:
        hashed_pw = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, 'bibliotecar');",
            (name, email, hashed_pw)
        )
        conn.commit()
        flash(f"Contul de bibliotecar pentru '{name}' a fost creat cu succes!", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare la crearea contului: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/admin/user/delete/<int:user_id>", methods=["POST"])
def admin_delete_user(user_id):
    """Sterge un utilizator din sistem (doar Admin)."""
    if "user_id" not in session or session["user_role"] != "admin":
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))

    # Nu permite stergerea propriului cont
    if user_id == session["user_id"]:
        flash("Nu iti poti sterge propriul cont de administrator!", "danger")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    user = conn.execute("SELECT id, name, role FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user:
        flash("Utilizatorul nu a fost gasit!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))

    # Nu permite stergerea altor admini
    if user["role"] == "admin":
        flash("Nu poti sterge un alt cont de administrator!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))

    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        flash(f"Contul utilizatorului '{user['name']}' a fost sters cu succes.", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare la stergerea contului: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("dashboard"))


@app.route("/admin/user/reset-password/<int:user_id>", methods=["POST"])
def admin_reset_password(user_id):
    """Reseteaza parola unui utilizator (doar Admin)."""
    if "user_id" not in session or session["user_role"] != "admin":
        flash("Acces neautorizat!", "danger")
        return redirect(url_for("index"))

    new_password = request.form.get("new_password", "").strip()

    if not new_password or len(new_password) < 6:
        flash("Parola noua trebuie sa aiba cel putin 6 caractere!", "warning")
        return redirect(url_for("dashboard"))

    conn = get_db_connection()
    user = conn.execute("SELECT id, name FROM users WHERE id = ?", (user_id,)).fetchone()

    if not user:
        flash("Utilizatorul nu a fost gasit!", "danger")
        conn.close()
        return redirect(url_for("dashboard"))

    try:
        hashed_pw = generate_password_hash(new_password)
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_pw, user_id))
        conn.commit()
        flash(f"Parola utilizatorului '{user['name']}' a fost resetata cu succes!", "success")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"Eroare la resetarea parolei: {e}", "danger")
    finally:
        conn.close()

    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
