import hashlib
from .db import get_connection

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verificar_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def listar_usuarios():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, nome, email, perfil, criado_em FROM usuarios ORDER BY id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def obter_usuario_por_email(email: str):
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None

def obter_usuario_por_id(id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, nome, email, perfil, criado_em FROM usuarios WHERE id = ?", (id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def criar_usuario(nome: str, email: str, password: str, perfil: str = "funcionario"):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO usuarios (nome, email, password, perfil) VALUES (?, ?, ?, ?)",
            (nome, email, hash_password(password), perfil)
        )
        conn.commit()
        return True
    except Exception:
        return False  # email duplicado
    finally:
        conn.close()

def atualizar_usuario(id: int, nome: str, email: str, perfil: str):
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE usuarios SET nome=?, email=?, perfil=? WHERE id=?",
            (nome, email, perfil, id)
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def alterar_password(id: int, password_nova: str):
    conn = get_connection()
    conn.execute(
        "UPDATE usuarios SET password=? WHERE id=?",
        (hash_password(password_nova), id)
    )
    conn.commit()
    conn.close()

def deletar_usuario(id: int):
    conn = get_connection()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conn.commit()
    conn.close()
