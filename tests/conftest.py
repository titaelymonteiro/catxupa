"""
Configuração partilhada dos testes.

Cada teste recebe uma base de dados SQLite *temporária e isolada* — nunca
tocamos em backend/models/farmacia.db. Isto significa que os testes podem
correr em qualquer máquina, em qualquer ordem, sem deixar sujidade nem
depender de dados que já lá estejam.
"""
import os
import sys

# Precisa de existir uma SECRET_KEY antes de qualquer import do backend,
# porque backend/auth/auth.py falha imediatamente sem ela.
os.environ.setdefault("SECRET_KEY", "chave-de-teste-nao-usar-em-producao")

# Torna o pacote "backend" importável quando o pytest corre a partir da
# pasta farmacia_api/ (raiz do projeto).
_RAIZ_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, _RAIZ_PROJETO)

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Cliente de testes (requests contra a app) ligado a uma base de
    dados SQLite nova a cada teste."""
    from backend.models import db as db_module

    db_ficheiro_teste = tmp_path / "farmacia_teste.db"
    monkeypatch.setattr(db_module, "DB_PATH", str(db_ficheiro_teste))
    db_module.init_db()  # cria as tabelas + utilizador admin de raiz

    from backend.main import app

    from backend.auth.rate_limit import resetar_tudo
    resetar_tudo()

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    """Faz login com o admin semeado por omissão e devolve o token."""
    resp = client.post(
        "/login",
        json={"email": "admin@farmacia.cv", "password": "admin123"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture()
def funcionario_headers(client, admin_headers):
    """Cria uma conta com perfil 'funcionario' (via admin) e devolve os
    headers de autenticação já autenticados como esse funcionário."""
    client.post(
        "/usuarios",
        json={
            "nome": "Funcionário Teste",
            "email": "funcionario@farmacia.cv",
            "password": "func1234",
            "perfil": "funcionario",
        },
        headers=admin_headers,
    )
    resp = client.post(
        "/login",
        json={"email": "funcionario@farmacia.cv", "password": "func1234"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def cliente_headers(client):
    """Regista uma conta pública (perfil 'cliente') e devolve os headers
    de autenticação para essa conta."""
    resp = client.post(
        "/registar",
        json={
            "nome": "Cliente Teste",
            "email": "cliente@example.com",
            "password": "abcd",
        },
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def criar_medicamento(client, admin_headers, **overrides):
    """Atalho para criar um medicamento de teste e devolver o seu id.

    Nota: init_db() semeia alguns medicamentos de demonstração (entre eles
    um "Paracetamol 500mg") sempre que a tabela está vazia. Por isso o nome
    por omissão aqui tem de ser único, para o teste apanhar sempre o
    medicamento que acabou de criar e não um dos dados de exemplo.
    """
    dados = {
        "nome": "Medicamento de Teste",
        "preco": 150.0,
        "estoque": 20,
        "validade": "2027-01-01",
        "categoria": "Categoria Teste",
    }
    dados.update(overrides)
    resp = client.post("/medicamentos", json=dados, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    listagem = client.get("/medicamentos", headers=admin_headers).json()
    candidatos = [m for m in listagem if m["nome"] == dados["nome"]]
    # Em caso de nomes repetidos, o mais recente é o de maior id.
    return max(candidatos, key=lambda m: m["id"])["id"]


def criar_venda(client, headers, med_id, medicamento_nome="Medicamento de Teste",
                 quantidade=1, preco_unitario=150.0, metodo="visa"):
    """Atalho para registar uma venda de teste e devolver o seu id."""
    subtotal = round(quantidade * preco_unitario, 2)
    resp = client.post(
        "/vendas",
        json={
            "itens": [
                {
                    "medicamento_id": med_id,
                    "medicamento_nome": medicamento_nome,
                    "quantidade": quantidade,
                    "preco_unitario": preco_unitario,
                    "subtotal": subtotal,
                }
            ],
            "pagamentos": [{"metodo": metodo, "valor": subtotal}],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["venda_id"]