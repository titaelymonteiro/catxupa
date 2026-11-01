"""
Teste manual AUTOMATIZADO dos LOTES (entrada de stock).

Verifica: registar um lote aumenta o stock; apagar um lote desconta o stock
(sem ficar negativo); medicamento/fornecedor inexistentes falham; e as
permissoes (funcionario pode gerir, cliente nao).

Usa uma base de dados TEMPORARIA — nao toca na tua farmacia.db.
Correr (na pasta que contem 'backend'):   py testar_lotes.py
"""
import os, sys, tempfile
os.environ.setdefault("SECRET_KEY", "chave-de-teste-lotes")
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # sobe de tests/ para a raiz do projeto
if _RAIZ not in sys.path:
    sys.path.insert(0, _RAIZ)
from fastapi.testclient import TestClient

_res = []
def verificar(desc, cond, detalhe=""):
    ok = bool(cond); _res.append(ok)
    print(f"  [{'OK   ' if ok else 'FALHOU'}] {desc}" + ("" if ok or not detalhe else f"\n           -> {detalhe}"))
    return ok
def titulo(t):
    print("\n" + t); print("-" * len(t))

def preparar():
    from backend.models import db as dbm
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False); tmp.close()
    dbm.DB_PATH = tmp.name; dbm.init_db()
    from backend.main import app
    try:
        from backend.auth.rate_limit import resetar_tudo; resetar_tudo()
    except Exception:
        pass
    return TestClient(app), tmp.name
def auth(t): return {"Authorization": f"Bearer {t}"}


def main():
    print("=" * 62)
    print("  TESTE DE LOTES (ENTRADA DE STOCK)  —  Farmacia CV")
    print("=" * 62)
    client, db_path = preparar()
    admin = auth(client.post("/login", json={"email": "admin@farmacia.cv", "password": "admin123"}).json()["access_token"])

    client.post("/medicamentos", headers=admin, json={
        "nome": "Med Lote Teste", "preco": 300.0, "estoque": 20, "validade": "2027-12-31", "categoria": "Teste"})
    meds = client.get("/medicamentos", headers=admin).json()
    med_id = max((m for m in meds if m["nome"] == "Med Lote Teste"), key=lambda m: m["id"])["id"]
    def stock(): return client.get(f"/medicamentos/{med_id}", headers=admin).json()["estoque"]

    client.post("/fornecedores", headers=admin, json={
        "nome": "Fornecedor Lote", "nif": "123", "telefone": "9", "email": "f@f.cv", "endereco": "Praia"})
    forns = client.get("/fornecedores", headers=admin).json()
    forn_id = max((f for f in forns if f["nome"] == "Fornecedor Lote"), key=lambda f: f["id"])["id"]

    def lote(qtd, numero, fornecedor_id=None, mid=None):
        return client.post("/lotes", headers=admin, json={
            "medicamento_id": mid or med_id, "fornecedor_id": fornecedor_id,
            "numero_lote": numero, "quantidade": qtd, "validade": "2027-06-01", "preco_custo": 100.0})

    titulo("Registar lotes aumenta o stock")
    s0 = stock()
    r = lote(15, "LOTE-001", fornecedor_id=forn_id)
    verificar("Registar lote de 15 unidades (201)", r.status_code == 201, r.text)
    lote_id = r.json().get("lote_id")
    verificar("Stock aumenta em 15 (entrada de mercadoria)", stock() == s0 + 15, f"stock={stock()} esperado={s0+15}")

    s1 = stock()
    r = lote(5, "LOTE-002")   # sem fornecedor
    verificar("Registar lote SEM fornecedor e permitido (201)", r.status_code == 201, r.text)
    verificar("Stock aumenta em 5 mesmo sem fornecedor", stock() == s1 + 5, f"stock={stock()}")

    titulo("Validacoes")
    r = lote(10, "LOTE-X", mid=999999)
    verificar("Lote para medicamento inexistente falha (404)", r.status_code == 404, r.text)
    r = lote(10, "LOTE-Y", fornecedor_id=999999)
    verificar("Lote com fornecedor inexistente falha (404)", r.status_code == 404, r.text)

    titulo("Apagar um lote desconta o stock")
    s2 = stock()
    r = client.delete(f"/lotes/{lote_id}", headers=admin)
    verificar("Apagar o lote de 15 (200)", r.status_code == 200, r.text)
    verificar("Stock desce em 15 ao apagar o lote", stock() == s2 - 15, f"stock={stock()}")

    r = client.get(f"/medicamentos/{med_id}/lotes", headers=admin)
    verificar("Listar os lotes de um medicamento (200, e uma lista)", r.status_code == 200 and isinstance(r.json(), list), r.text)

    titulo("Permissoes")
    client.post("/usuarios", headers=admin, json={"nome": "Zeca", "email": "zeca.l@farmacia.cv", "password": "func1234", "perfil": "funcionario"})
    func = auth(client.post("/login", json={"email": "zeca.l@farmacia.cv", "password": "func1234"}).json()["access_token"])
    r = client.post("/lotes", headers=func, json={"medicamento_id": med_id, "fornecedor_id": None,
                    "numero_lote": "LOTE-FUNC", "quantidade": 3, "validade": "2027-06-01", "preco_custo": 50.0})
    verificar("Funcionario PODE gerir lotes (201)", r.status_code == 201, r.text)

    r = client.post("/registar", json={"nome": "Cli", "email": "cli.l@example.com", "password": "1234"})
    cli = auth(r.json()["access_token"])
    r = client.post("/lotes", headers=cli, json={"medicamento_id": med_id, "fornecedor_id": None,
                    "numero_lote": "LOTE-CLI", "quantidade": 3, "validade": "2027-06-01", "preco_custo": 50.0})
    verificar("Cliente NAO pode gerir lotes (403)", r.status_code == 403, r.text)

    total, passou = len(_res), sum(_res)
    print("\n" + "=" * 62)
    print(f"  RESULTADO: {passou}/{total} passos OK")
    print("  🎉 Lotes a funcionar corretamente." if passou == total else f"  ⚠️  {total-passou} passo(s) falharam.")
    print("=" * 62)
    try: os.unlink(db_path)
    except OSError: pass
    sys.exit(0 if passou == total else 1)

if __name__ == "__main__":
    main()