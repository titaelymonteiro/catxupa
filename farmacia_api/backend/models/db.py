import sqlite3
import os
import hashlib

DB_PATH = os.path.join(os.path.dirname(__file__), "farmacia.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicamentos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            preco     REAL    NOT NULL,
            estoque   INTEGER NOT NULL,
            validade  TEXT,
            categoria TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL DEFAULT 'Sem nome',
            email     TEXT    NOT NULL UNIQUE,
            password  TEXT    NOT NULL,
            perfil    TEXT    NOT NULL DEFAULT 'funcionario',
            criado_em TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            telefone  TEXT,
            email     TEXT,
            endereco  TEXT,
            criado_em TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente     TEXT    NOT NULL DEFAULT 'Cliente Geral',
            cliente_id  INTEGER,
            total       REAL    NOT NULL,
            criado_em   TEXT    DEFAULT (datetime('now')),
            criado_por  TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS venda_itens (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id         INTEGER NOT NULL,
            medicamento_id   INTEGER NOT NULL,
            medicamento_nome TEXT    NOT NULL,
            quantidade       INTEGER NOT NULL,
            preco_unitario   REAL    NOT NULL,
            subtotal         REAL    NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id)
        )
    """)

    # Migrar colunas antigas
    for tabela, col, definition in [
        ("usuarios", "nome",       "TEXT NOT NULL DEFAULT 'Sem nome'"),
        ("usuarios", "perfil",     "TEXT NOT NULL DEFAULT 'funcionario'"),
        ("usuarios", "criado_em",  "TEXT DEFAULT (datetime('now'))"),
        ("vendas",   "cliente_id", "INTEGER"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {col} {definition}")
        except Exception:
            pass

    # Admin padrão
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", ("admin@farmacia.cv",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nome, email, password, perfil) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin@farmacia.cv", hash_password("admin123"), "admin")
        )

    # Medicamentos de exemplo
    cursor.execute("SELECT COUNT(*) FROM medicamentos")
    if cursor.fetchone()[0] == 0:
        exemplos = [
            ("Paracetamol 500mg", 250.0, 50, "2028-12-01", "Analgésico"),
            ("Amoxicilina 250mg", 1200.0, 8,  "2028-08-15", "Antibiótico"),
            ("Ibuprofeno 400mg",  400.0, 30, "2027-06-30", "Anti-inflamatório"),
            ("Omeprazol 20mg",    600.0, 20, "2030-03-10", "Antiácido"),
            ("Metformina 500mg",  350.0, 5,  "2027-11-20", "Antidiabético"),
        ]
        cursor.executemany(
            "INSERT INTO medicamentos (nome, preco, estoque, validade, categoria) VALUES (?,?,?,?,?)",
            exemplos
        )

    conn.commit()
    conn.close()
