# SmartLibrary

SmartLibrary este o aplicație web minimalistă pentru gestiunea catalogului de cărți și administrarea rezervărilor dintr-o bibliotecă, dezvoltată în Python folosind micro-framework-ul Flask și baza de date relațională SQLite.

## Descriere și Funcționalități

Sistemul implementează un flux complet de rezervare și împrumut fizic de cărți, fiind structurat pe baza a trei roluri de utilizatori (Cititor, Bibliotecar, Administrator) plus suport pentru Vizitatori neînregistrați.

### Funcționalități Principale:
*   **Gestiune Catalog:** Vizualizarea cărților disponibile cu filtrare în timp real la nivelul clientului (JavaScript) după titlu, autor sau categorie, împreună cu paginare dinamică.
*   **Sistem de Autentificare Securizat:** Înregistrare și conectare cu parole criptate prin hashing PBKDF2 și stocare securizată în sesiune.
*   **Fluxul de Rezervare (Cititori):** Cititorii autentificați pot rezerva o carte disponibilă. Sistemul scade automat stocul și menține rezervarea activă timp de 48 de ore. Cititorii își pot anula manual rezervările pending direct din propriul dashboard.
*   **Curățare Automată:** Aplicația rulează un proces automat la nivel de backend pentru anularea rezervărilor neridicate în termenul limită de 48 de ore, returnând automat exemplarele în stoc.
*   **Panou Administrare Bibliotecar:** Permite adăugarea, editarea și ștergerea cărților (inclusiv încărcarea copertelor pe server). Bibliotecarii pot valida fizic ridicarea cărților (definind o perioadă de împrumut personalizată, implicit 14 zile) și pot confirma returnarea lor.
*   **Panou Administrare General (Admin):** Permite gestiunea conturilor, crearea de utilizatori cu drepturi de bibliotecar, resetarea parolelor și ștergerea conturilor de cititori.

## Cerințe de Sistem

Pentru rularea aplicației pe calculatorul local, sunt necesare:
*   Python 3.10 sau o versiune mai nouă
*   pip (managerul de pachete pentru Python)

## Configurare și Instalare

1. Instalați dependențele necesare:
   ```bash
   pip install Flask
   ```
   *Notă: Modulele precum sqlite3, os și datetime fac parte din biblioteca standard Python și nu necesită instalare separată.*

2. Inițializați schema bazei de date și datele de test predefinite:
   ```bash
   python init_db.py
   ```
   Această comandă rulează instrucțiunile DDL din `schema.sql` și generează fișierul local al bazei de date `library.db`.

## Rulare

Porniți serverul local de dezvoltare prin rularea scriptului principal:
```bash
python app.py
```

După inițializare, aplicația va fi activă pe serverul local. Accesați interfața utilizatorului prin browser-ul web la adresa:
*   URL: http://127.0.0.1:5000

## Conturi de Test Predefinite

Baza de date este inițializată cu următoarele conturi de dezvoltare pentru testarea rolurilor și permisiunilor (parola comună este `12345678`):

| Rol | Email / Utilizator | Parolă |
| :--- | :--- | :--- |
| **Administrator** | `admin@smartlibrary.com` | `12345678` |
| **Bibliotecar** | `dan.constantin@smartlibrary.com` | `12345678` |

*Notă: Conturile de tip Cititor pot fi create dinamic direct prin formularul de înregistrare al aplicației.*

## Structura Directoarelor

*   `app.py` - Controller-ul principal al aplicației (gestionează rutele, conexiunile la baza de date și regulile de business).
*   `init_db.py` - Script pentru inițializarea și popularea bazei de date.
*   `schema.sql` - Structura SQL a tabelelor, constrângerile de integritate și cheile externe (cascade delete).
*   `static/` - Fișiere statice accesibile direct de client (cod CSS personalizat, coperți de cărți încărcate).
*   `templates/` - Șabloane HTML randate dinamic prin intermediul motorului Jinja2.
