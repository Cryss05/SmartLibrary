import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "library.db")
SCHEMA_FILE = os.path.join(BASE_DIR, "schema.sql")

def init_db():
    print("Se initializeaza baza de date...")
    
    if not os.path.exists(SCHEMA_FILE):
        print(f"Eroare: Fisierul {SCHEMA_FILE} nu a fost gasit!")
        return

    # Conectare la baza de date
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Citirea si rularea schemei SQL
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    try:
        cursor.executescript(schema_sql)
        print("Tabelele au fost create cu succes.")
    except sqlite3.Error as e:
        print(f"Eroare la crearea tabelelor: {e}")
        conn.close()
        return

    # Inserarea datelor de test (Seed Data)
    print("Se insereaza datele de test...")
    
    # 1. Utilizatori
    users_data = [
        ("Administrator", "admin@smartlibrary.com", generate_password_hash("12345678"), "admin"),
        ("Bibliotecar Dan Constantin", "dan.constantin@smartlibrary.com", generate_password_hash("12345678"), "bibliotecar"),
        ("Bibliotecar Anamaria Popa", "anamaria.popa@smartlibrary.com", generate_password_hash("12345678"), "bibliotecar")
    ]
    
    try:
        cursor.executemany(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?);",
            users_data
        )
        print("Utilizatorii de test au fost adaugati.")
    except sqlite3.Error as e:
        print(f"Eroare la adaugarea utilizatorilor: {e}")
        conn.close()
        return

    # 2. Carti
    books_data = [
        ("Amintiri din copilarie", "Ion Creanga", "Fictiune", 
         "Amintirile din copilarie alcatuiesc pagini literare, pline de emotionante si fermecatoare evocari din copilaria povestitorului... Creanga este un mare creator de chipuri si icoane. Toate figurile au relieful lor bine conturat, incepand cu buna lui mama, Smaranda, pana la mos Bodranga si mos Luca, harabagiul din Humulesti, care l-a dus surghiun la seminarul Socolei...\n\n"
         "Fondul Amintirilor din copilarie e insusi fondul sufletesc al poporului roman: sincer si bun pana la duiosie, rabdator si cuminte, voios, mucalit si istet, si de o dulce si statornica resemnare in vremuri grele, care l-a facut sa iasa biruitor de-a lungul veacurilor... Intr-o perfecta armonie cu fondul, stilul povestitorului este narativ. Cursul povestirii, incet sau iute, linistit sau impetuos, e insusi mersul gandurilor si sentimentelor sale, dupa ce au trecut prin stavilarul constiintei artistice. In clipele atat de grele ale creatiei, Creanga suferea chinuri cumplite, caci el se lupta sa stavileasca torentul si sa-i potrivesca mersul regulat, dupa cursul simtirii si dupa ritmul inimii sale.\n\n"
         "Materialul lingvistic e foarte bogat in scrierile lui Creanga. El fugea cu oroare de neologisme, pe care le-a definit intr-un autograf, gasit mai tarziu pe fila unei gramatici: \"Neologisme se cheama toate cuvintele introduse in limba, unele fara trebuinta, si pentru care putem gasi un cuvant romanesc corespunzator...\". Cand se intampla totusi sa-i scape sub condei vreun neologism, doua, le inlocuia repede, punand in loc cuvinte scoase din graiul taranului moldovean. - Nicolae Timiras", 
         "/static/uploads/aminitri-din-copilarie.jpg", 5, 5),
         
        ("Poezii", "Mihai Eminescu", "Poezie", 
         "Fara nici o indoiala, cel mai studiat autor roman a fost si este, si astazi, Mihai Eminescu. Opera, dar si viata ii sunt prelucrate in laboratoare cu specializari variate, cu lupe istorico-literare, lingvistice, stilistice, prozodice, teoretico-literare, comparatiste, filozofice, economice, politice, istorice, sociologice, ziaristice, medicale s.a.m.d. Efortul se multiplica in scoala prin cautari constante de a stabiili si, mai ales, a justifica locul pe care opera eminesciana il ocupa in cultura nationala si universala. Se cauta, de asemenea, si in sala de curs, si in intimitatea criticii savante elementele care sa valideze fie modernitatea, fie caducitatea ei.\n\nLucian Pricop", 
         "/static/uploads/poezii_Eminescu.jpg", 3, 2), # 1 copie este imprumutata
         
        ("Morometii", "Marin Preda", "Roman", 
         "Îi datorăm lui Marin Preda mai mult decât majorităţii istoricilor şi filosofilor contemporani care reflectează asupra destinului românesc. Efectul relecturii romanelor, nuvelelor, scrierilor sale în general, este cel mai eficient antidot împotriva mitului „deşertului cultural\" de care a fost suspectat spaţiul românesc în cea de a doua jumătate a secolului XX.", 
         "/static/uploads/morometii.jpg", 4, 3), # 1 copie este rezervata (pending)
         
        ("Ion", "Liviu Rebreanu", "Roman", 
         "Nicăieri în literatura română viața satului n-a fost evocată cu atâta forță realistă, atât de viguros și pătrunzător. Condiția lui Ion rezumă tragedia istorică a țăranului fără pământ și dacă parvenirea socială a personajului este reprezentativă doar pentru o mică parte a acestei țărănimi, ambiția de care el este devorat definește sufletul țărănesc în general. Teribilă, sforțarea lui Ion de a-și depăși condiția capătă dimensiuni universale și înfrângerea sa în lupta cu soarta implacabilă aduce aminte de prăbușirea eroilor din tragediile antice. Povestea ascensiunii și surpării lui Ion adună în cuprinsul ei, concentrată, închisă parcă într-un cerc, întreaga existență de altădată a Transilvaniei românești. Lumea țărănească, cu straturile ei, nu fără comunicare unele cu altele, dar vizibil delimitate, lumea intelectualității satului: învățătorul, preotul, apoi autoritățile: primarul, jandarmul, notarul, lista politicienilor în goană după voturi; de asemenea datinile ardelene specifice, legate de horă, nuntă, înmormântare, într-un cuvânt – viața satului în toate înfățișările sale alcătuiește în cuprinsul romanului un amplu și magistral caleidoscop. Ion este o densă monografie sau, mai precis, o epopee a satului românesc de peste munți…\n\nDumitru MICU", 
         "/static/uploads/ion.jpg", 2, 2)
    ]
    
    try:
        cursor.executemany(
            "INSERT INTO books (title, author, category, description, cover_url, total_copies, available_copies) VALUES (?, ?, ?, ?, ?, ?, ?);",
            books_data
        )
        print("Cartile de test au fost adaugate.")
    except sqlite3.Error as e:
        print(f"Eroare la adaugarea cartilor: {e}")
        conn.close()
        return



    # Salvam modificarile
    conn.commit()
    conn.close()
    print("Initializarea bazei de date s-a incheiat cu succes!")

if __name__ == "__main__":
    init_db()
