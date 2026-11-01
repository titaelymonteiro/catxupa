import sqlite3
import os
import hashlib
import hmac
import secrets

DB_PATH = os.path.join(os.path.dirname(__file__), "farmacia.db")

# Parâmetros do PBKDF2 (stdlib, sem dependências externas).
_PBKDF2_ITERATIONS = 200_000
_PBKDF2_ALGO = "pbkdf2_sha256"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Gera um hash com salt usando PBKDF2-SHA256.
    Formato guardado: pbkdf2_sha256$<iteracoes>$<salt_hex>$<hash_hex>
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{_PBKDF2_ALGO}${_PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"

def verificar_password(password: str, hashed: str) -> bool:
    """Verifica a password. Retrocompatível com hashes SHA-256 antigos
    (sem salt) para que os utilizadores existentes continuem a entrar."""
    if not hashed:
        return False
    if hashed.startswith(_PBKDF2_ALGO + "$"):
        try:
            _algo, iteracoes, salt_hex, hash_hex = hashed.split("$")
            dk = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), int(iteracoes)
            )
            return hmac.compare_digest(dk.hex(), hash_hex)
        except Exception:
            return False
    # Legado: SHA-256 simples (hex de 64 chars)
    legacy = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(legacy, hashed)

def is_hash_legado(hashed: str) -> bool:
    """True se o hash ainda está no formato antigo (SHA-256 sem salt)."""
    return bool(hashed) and not hashed.startswith(_PBKDF2_ALGO + "$")

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
            latitude  REAL,
            longitude REAL,
            criado_em TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendas (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente     TEXT    NOT NULL DEFAULT 'Cliente Geral',
            cliente_id  INTEGER,
            total       REAL    NOT NULL,
            valor_recebido REAL,
            troco       REAL    NOT NULL DEFAULT 0,
            anulada     INTEGER NOT NULL DEFAULT 0,
            anulada_em  TEXT,
            anulada_por TEXT,
            motivo_anulacao TEXT,
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS venda_pagamentos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id    INTEGER NOT NULL,
            metodo      TEXT    NOT NULL,
            valor       REAL    NOT NULL,
            FOREIGN KEY (venda_id) REFERENCES vendas(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devolucoes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            venda_id         INTEGER NOT NULL,
            medicamento_id   INTEGER NOT NULL,
            medicamento_nome TEXT    NOT NULL,
            quantidade       INTEGER NOT NULL,
            valor            REAL    NOT NULL,
            motivo           TEXT,
            criado_por       TEXT,
            criado_em        TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (venda_id) REFERENCES vendas(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT    NOT NULL,
            acao          TEXT    NOT NULL,
            entidade      TEXT    NOT NULL,
            entidade_id   TEXT,
            descricao     TEXT    NOT NULL,
            criado_em     TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fornecedores (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    NOT NULL,
            nif       TEXT,
            telefone  TEXT,
            email     TEXT,
            endereco  TEXT,
            latitude  REAL,
            longitude REAL,
            criado_em TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lotes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            medicamento_id  INTEGER NOT NULL,
            fornecedor_id   INTEGER,
            numero_lote     TEXT    NOT NULL,
            quantidade      INTEGER NOT NULL,
            validade        TEXT    NOT NULL,
            preco_custo     REAL,
            criado_em       TEXT    DEFAULT (datetime('now')),
            criado_por      TEXT,
            FOREIGN KEY (medicamento_id) REFERENCES medicamentos(id),
            FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id      INTEGER NOT NULL,
            estado          TEXT    NOT NULL DEFAULT 'pendente',
            total           REAL    NOT NULL DEFAULT 0,
            nota            TEXT,
            morada_entrega  TEXT,
            entrega_lat     REAL,
            entrega_lng     REAL,
            metodo_pagamento TEXT,
            pago            INTEGER NOT NULL DEFAULT 0,
            cartao_ultimos4 TEXT,
            criado_em       TEXT    DEFAULT (datetime('now')),
            atualizado_em   TEXT,
            atualizado_por  TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedido_itens (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id         INTEGER NOT NULL,
            medicamento_id    INTEGER NOT NULL,
            medicamento_nome  TEXT    NOT NULL,
            quantidade        INTEGER NOT NULL,
            preco_unitario    REAL    NOT NULL,
            subtotal          REAL    NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id),
            FOREIGN KEY (medicamento_id) REFERENCES medicamentos(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notificacoes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo       TEXT    NOT NULL,
            mensagem   TEXT    NOT NULL,
            link       TEXT,
            chave      TEXT,
            lida       INTEGER NOT NULL DEFAULT 0,
            criado_em  TEXT    DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pontos_historico (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id  INTEGER NOT NULL,
            tipo        TEXT    NOT NULL,
            pontos      INTEGER NOT NULL,
            motivo      TEXT,
            venda_id    INTEGER,
            criado_em   TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (venda_id) REFERENCES vendas(id)
        )
    """)

    # Migrar colunas antigas
    for tabela, col, definition in [
        ("usuarios", "nome",          "TEXT NOT NULL DEFAULT 'Sem nome'"),
        ("usuarios", "perfil",        "TEXT NOT NULL DEFAULT 'funcionario'"),
        ("usuarios", "criado_em",     "TEXT DEFAULT (datetime('now'))"),
        ("vendas",   "cliente_id",    "INTEGER"),
        ("vendas",   "valor_recebido", "REAL"),
        ("vendas",   "troco",         "REAL NOT NULL DEFAULT 0"),
        ("vendas",   "anulada",       "INTEGER NOT NULL DEFAULT 0"),
        ("vendas",   "anulada_em",    "TEXT"),
        ("vendas",   "anulada_por",   "TEXT"),
        ("vendas",   "motivo_anulacao", "TEXT"),
        ("medicamentos", "preco_custo", "REAL"),
        ("medicamentos", "fornecedor_id", "INTEGER"),
        ("usuarios", "cliente_id", "INTEGER"),
        ("medicamentos", "requer_receita", "INTEGER NOT NULL DEFAULT 0"),
        ("venda_itens", "receita_numero", "TEXT"),
        ("venda_itens", "receita_medico", "TEXT"),
        ("clientes", "pontos_fidelidade", "INTEGER NOT NULL DEFAULT 0"),
        ("vendas", "pontos_ganhos", "INTEGER NOT NULL DEFAULT 0"),
        ("vendas", "pontos_resgatados", "INTEGER NOT NULL DEFAULT 0"),
        ("vendas", "desconto_pontos", "REAL NOT NULL DEFAULT 0"),
        ("pedidos", "morada_entrega", "TEXT"),
        ("pedidos", "entrega_lat", "REAL"),
        ("pedidos", "entrega_lng", "REAL"),
        ("pedidos", "metodo_pagamento", "TEXT"),
        ("pedidos", "pago", "INTEGER NOT NULL DEFAULT 0"),
        ("pedidos", "cartao_ultimos4", "TEXT"),
        ("clientes", "latitude", "REAL"),
        ("clientes", "longitude", "REAL"),
        ("fornecedores", "latitude", "REAL"),
        ("fornecedores", "longitude", "REAL"),
        ("notificacoes", "chave", "TEXT"),
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