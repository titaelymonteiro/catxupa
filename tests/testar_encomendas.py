"""
Teste manual AUTOMATIZADO do fluxo de encomendas online.

Corre o percurso completo (registar cliente -> encomendar -> staff confirmar ->
verificar stock -> cancelar -> repor stock) e imprime um relatorio passo-a-passo
com OK/FALHOU para cada passo.

IMPORTANTE: usa uma base de dados TEMPORARIA. Nao toca na tua farmacia.db.
Nao precisas sequer de ter o servidor a correr.

Como correr (na pasta que contem 'backend'):
    py testar_encomendas.py
"""
import os
import sys
import tempfile

# SECRET_KEY tem de existir antes de importar o backend
os.environ.setdefault("SECRET_KEY", "chave-de-teste-encomendas")

# tornar o pacote 'backend' importavel a partir da raiz do projeto
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # sobe de tests/ para a raiz do projeto
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)

from fastapi.testclient import TestClient

# ---- relatorio -------------------------------------------------------------
_resultados = []

def verificar(descricao, condicao, detalhe=""):
    ok = bool(condicao)
    _resultados.append(ok)
    marca = "OK   " if ok else "FALHOU"
    linha = f"  [{marca}] {descricao}"
    if not ok and detalhe:
        linha += f"\n           -> {detalhe}"
    print(linha)
    return ok

def titulo(txt):
    print("\n" + txt)
    print("-" * len(txt))

# ---- preparar app com BD temporaria ----------------------------------------
def preparar_cliente():
    from backend.models import db as db_module
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_module.DB_PATH = tmp.name          # aponta para a BD temporaria
    db_module.init_db()                    # cria tabelas + admin + medicamentos demo
    from backend.main import app
    try:
        from backend.auth.rate_limit import resetar_tudo
        resetar_tudo()
    except Exception:
        pass
    return TestClient(app), tmp.name

def auth(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    print("=" * 62)
    print("  TESTE DO FLUXO DE ENCOMENDAS ONLINE  —  Farmacia CV")
    print("=" * 62)

    client, db_path = preparar_cliente()

    # login admin
    r = client.post("/login", json={"email": "admin@farmacia.cv", "password": "admin123"})
    admin = auth(r.json()["access_token"])

    # criar um medicamento com stock conhecido (20)
    client.post("/medicamentos", headers=admin, json={
        "nome": "Med Encomenda Teste", "preco": 200.0, "estoque": 20,
        "validade": "2027-12-31", "categoria": "Teste"})
    meds = client.get("/medicamentos", headers=admin).json()
    med = max((m for m in meds if m["nome"] == "Med Encomenda Teste"), key=lambda m: m["id"])
    med_id = med["id"]

    def stock():
        return client.get(f"/medicamentos/{med_id}", headers=admin).json()["estoque"]

    # registar um cliente (fica com cliente_id ligado automaticamente)
    r = client.post("/registar", json={
        "nome": "Ana Cliente", "email": "ana.teste@example.com", "password": "1234"})
    cliente = auth(r.json()["access_token"])

    # ============================================================
    titulo("CENARIO A — O cliente faz uma encomenda")

    r = client.get("/catalogo", headers=cliente)
    item_cat = next((m for m in r.json() if m["nome"] == "Med Encomenda Teste"), {})
    verificar("Catalogo acessivel ao cliente (200)", r.status_code == 200, r.text)
    verificar("Catalogo esconde a quantidade exata de stock",
              "estoque" not in item_cat and item_cat.get("disponivel") is True, str(item_cat))

    r = client.post("/pedidos", headers=cliente,
                    json={"itens": [{"medicamento_id": med_id, "quantidade": 5}], "nota": "Entregar de manha"})
    verificar("Encomenda criada com sucesso (201)", r.status_code == 201, r.text)
    pedido_id = r.json().get("pedido_id")

    verificar("Stock NAO desce ao encomendar (continua 20)", stock() == 20, f"stock={stock()}")

    r = client.get("/meus-pedidos", headers=cliente)
    meu = next((p for p in r.json() if p["id"] == pedido_id), {})
    verificar("Encomenda aparece em 'os meus pedidos' como PENDENTE",
              meu.get("estado") == "pendente", str(meu))

    # ============================================================
    titulo("CENARIO B — O staff confirma e conclui")

    r = client.get("/notificacoes", headers=admin)
    verificar("Foi criada notificacao de novo pedido para o staff",
              any(n["tipo"] == "pedido_novo" for n in r.json()), r.text)

    r = client.put(f"/pedidos/{pedido_id}/estado", headers=admin, json={"estado": "confirmado"})
    verificar("Staff confirma a encomenda (200)", r.status_code == 200, r.text)
    verificar("Stock DESCE ao confirmar (20 - 5 = 15)", stock() == 15, f"stock={stock()}")

    r1 = client.put(f"/pedidos/{pedido_id}/estado", headers=admin, json={"estado": "pronto"})
    r2 = client.put(f"/pedidos/{pedido_id}/estado", headers=admin, json={"estado": "concluido"})
    verificar("Estado avanca pronto -> concluido", r1.status_code == 200 and r2.status_code == 200,
              f"{r1.status_code}/{r2.status_code}")

    r = client.put(f"/pedidos/{pedido_id}/estado", headers=admin, json={"estado": "pendente"})
    verificar("Nao deixa alterar uma encomenda ja concluida (400)", r.status_code == 400, r.text)

    # ============================================================
    titulo("CENARIO C — Cancelamentos e reposicao de stock")

    # cliente cancela enquanto pendente (stock nao mexe)
    r = client.post("/pedidos", headers=cliente, json={"itens": [{"medicamento_id": med_id, "quantidade": 3}]})
    ped2 = r.json()["pedido_id"]
    r = client.post(f"/meus-pedidos/{ped2}/cancelar", headers=cliente)
    verificar("Cliente cancela a sua encomenda pendente (200)", r.status_code == 200, r.text)
    verificar("Stock intacto apos cancelar um pendente (continua 15)", stock() == 15, f"stock={stock()}")

    # staff confirma e depois cancela -> stock volta
    r = client.post("/pedidos", headers=cliente, json={"itens": [{"medicamento_id": med_id, "quantidade": 4}]})
    ped3 = r.json()["pedido_id"]
    client.put(f"/pedidos/{ped3}/estado", headers=admin, json={"estado": "confirmado"})
    verificar("Apos confirmar o 3o pedido, stock = 15 - 4 = 11", stock() == 11, f"stock={stock()}")
    client.put(f"/pedidos/{ped3}/estado", headers=admin, json={"estado": "cancelado"})
    verificar("Ao cancelar um pedido confirmado, o stock VOLTA (11 + 4 = 15)", stock() == 15, f"stock={stock()}")

    # ============================================================
    titulo("CENARIO D — Regras e permissoes")

    r = client.put(f"/pedidos/{pedido_id}/estado", headers=admin, json={"estado": "inventado"})
    verificar("Estado invalido e recusado (400)", r.status_code == 400, r.text)

    # funcionario (sem cliente_id) nao pode encomendar
    client.post("/usuarios", headers=admin, json={
        "nome": "Zeca Funcionario", "email": "zeca@farmacia.cv", "password": "func1234", "perfil": "funcionario"})
    rf = client.post("/login", json={"email": "zeca@farmacia.cv", "password": "func1234"})
    func = auth(rf.json()["access_token"])
    r = client.post("/pedidos", headers=func, json={"itens": [{"medicamento_id": med_id, "quantidade": 1}]})
    verificar("Um funcionario (nao-cliente) NAO pode encomendar (400)", r.status_code == 400, r.text)

    # outro cliente nao ve os pedidos do primeiro
    r = client.post("/registar", json={"nome": "Beto", "email": "beto.teste@example.com", "password": "1234"})
    beto = auth(r.json()["access_token"])
    r = client.get("/meus-pedidos", headers=beto)
    verificar("Um cliente novo nao ve encomendas de outros (lista vazia)", r.json() == [], r.text)

    # ---- resumo ----
    total = len(_resultados)
    passou = sum(_resultados)
    print("\n" + "=" * 62)
    print(f"  RESULTADO: {passou}/{total} passos OK")
    if passou == total:
        print("  🎉 Tudo a funcionar! O fluxo de encomendas online esta correto.")
    else:
        print(f"  ⚠️  {total - passou} passo(s) falharam — ver acima.")
    print("=" * 62)

    # limpar a BD temporaria
    try:
        os.unlink(db_path)
    except OSError:
        pass

    sys.exit(0 if passou == total else 1)


if __name__ == "__main__":
    main()