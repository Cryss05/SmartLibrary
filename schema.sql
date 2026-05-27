-- Activam constrangerile pentru cheile externe
PRAGMA foreign_keys = ON;

-- Stergem tabelele in ordine inversa a dependentelor pentru a evita erorile de constrangere
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS books;
DROP TABLE IF EXISTS users;

-- Tabel pentru Utilizatori
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('cititor', 'bibliotecar', 'admin')) DEFAULT 'cititor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabel pentru Catalogul de Carti
CREATE TABLE books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    cover_url TEXT,
    total_copies INTEGER NOT NULL DEFAULT 1,
    available_copies INTEGER NOT NULL DEFAULT 1
);

-- Tabel pentru Rezervari / Imprumuturi
CREATE TABLE reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    book_id INTEGER NOT NULL,
    status TEXT CHECK(status IN ('pending', 'borrowed', 'returned', 'cancelled')) DEFAULT 'pending',
    reserved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL, -- Termen limita pentru ridicare (48 ore)
    borrowed_at TIMESTAMP,         -- Data la care a fost ridicata fizic cartea
    return_deadline TIMESTAMP,     -- Termen limita pentru returnare
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
);
