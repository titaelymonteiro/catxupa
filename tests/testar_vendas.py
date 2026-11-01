"""
Teste manual AUTOMATIZADO do fluxo de VENDAS (POS).

Verifica: desconto de stock, integridade do preco (servidor manda),
metodos de pagamento (cartao24/visa), pagamento a mais/menos, e anulacao
com reposicao de stock.

Usa uma base de dados TEMPORARIA — nao toca na tua farmacia.db.
Nao precisas do servidor a correr.

Correr (na pasta que contem 'backend'):   py testar_vendas.py
"""
import os, sys, tempfile
os.environ.setdefault("SECRET_KEY", "chave-de-teste-vendas")
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
    print("  TESTE DO FLUXO DE VENDAS  —  Farmacia CV")
    print("=" * 62)
    client, db_path = preparar()

    admin = auth(client.post("/login", json={"email": "admin@farmacia.cv", "password": "admin123"}).json()["access_token"])
    client.post("/medicamentos", headers=admin, json={
        "nome": "Med Venda Teste", "preco": 200.0, "estoque": 30, "validade": "2027-12-31", "categoria": "Teste"})
    meds = client.get("/medicamentos", headers=admin).json()
    med_id = max((m for m in meds if m["nome"] == "Med Venda Teste"), key=lambda m: m["id"])["id"]
    def stock(): return client.get(f"/medicamentos/{med_id}", headers=admin).json()["estoque"]
    def item(qtd, preco=200.0): return {"medicamento_id": med_id, "medicamento_nome": "Med Venda Teste",
                                        "quantidade": qtd, "preco_unitario": preco, "subtotal": round(preco*qtd, 2)}

    titulo("Registo de venda e stock")
    s0 = stock()
    r = client.post("/vendas", headers=admin, json={"itens": [item(2)], "pagamentos": [{"metodo": "visa", "valor": 400}]})
    verificar("Venda simples com visa (201)", r.status_code == 201, r.text)
    verificar("Stock desce na venda (2 unidades)", stock() == s0 - 2, f"stock={stock()} esperado={s0-2}")

    titulo("Integridade do preco (o servidor manda)")
    s1 = stock()
    # cliente tenta 'preco 1' mas paga o total real (400) -> servidor usa o preco da BD
    r = client.post("/vendas", headers=admin, json={"itens": [item(2, preco=1.0)], "pagamentos": [{"metodo": "visa", "valor": 400}]})
    vid = r.json().get("venda_id")
    det = client.get(f"/vendas/{vid}", headers=admin).json() if vid else {}
    preco_guardado = det.get("itens", [{}])[0].get("preco_unitario")
    verificar("Ignora o preco enviado pelo cliente (usa 200 da BD, nao 1)", preco_guardado == 200.0, f"guardado={preco_guardado}")

    titulo("Validacoes de pagamento e itens")
    r = client.post("/vendas", headers=admin, json={"itens": [item(1)], "pagamentos": [{"metodo": "dinheiro", "valor": 200}]})
    verificar("Metodo de pagamento invalido e recusado (400)", r.status_code == 400, r.text)
    r = client.post("/vendas", headers=admin, json={"itens": [], "pagamentos": [{"metodo": "visa", "valor": 0}]})
    verificar("Venda sem itens e recusada (400)", r.status_code == 400, r.text)
    r = client.post("/vendas", headers=admin, json={"itens": [item(1)], "pagamentos": []})
    verificar("Venda sem pagamentos e recusada (400)", r.status_code == 400, r.text)
    r = client.post("/vendas", headers=admin, json={"itens": [item(1)], "pagamentos": [{"metodo": "visa", "valor": 100}]})
    verificar("Pagar a MENOS que o total e recusado (400)", r.status_code == 400, r.text)
    r = client.post("/vendas", headers=admin, json={"itens": [item(1)], "pagamentos": [{"metodo": "visa", "valor": 500}]})
    verificar("Pagar a MAIS por cartao e recusado (400)", r.status_code == 400, r.text)
    r = client.post("/vendas", headers=admin, json={"itens": [item(99999)], "pagamentos": [{"metodo": "visa", "valor": 200}]})
    verificar("Stock insuficiente e recusado (400)", r.status_code == 400, r.text)

    titulo("Anulacao de venda (repoe stock)")
    s2 = stock()
    r = client.post("/vendas", headers=admin, json={"itens": [item(5)], "pagamentos": [{"metodo": "visa", "valor": 1000}]})
    vid = r.json()["venda_id"]
    verificar("Venda de 5 unidades desconta stock", stock() == s2 - 5, f"stock={stock()}")
    r = client.post(f"/vendas/{vid}/anular", headers=admin, json={"motivo": "engano"})
    verificar("Anular a venda (200)", r.status_code == 200, r.text)
    verificar("Stock reposto apos anular (volta ao valor anterior)", stock() == s2, f"stock={stock()}")
    det = client.get(f"/vendas/{vid}", headers=admin).json()
    verificar("Venda fica marcada como anulada", det.get("anulada") == 1, str(det.get("anulada")))
    r = client.post(f"/vendas/{vid}/anular", headers=admin, json={"motivo": "outra vez"})
    verificar("Anular duas vezes e recusado (400)", r.status_code == 400, r.text)
    r = client.post("/vendas/999999/anular", headers=admin, json={})
    verificar("Anular venda inexistente devolve 404", r.status_code == 404, r.text)

    titulo("Permissoes")
    client.post("/usuarios", headers=admin, json={"nome": "Zeca", "email": "zeca.v@farmacia.cv", "password": "func1234", "perfil": "funcionario"})
    func = auth(client.post("/login", json={"email": "zeca.v@farmacia.cv", "password": "func1234"}).json()["access_token"])
    r = client.post("/vendas", headers=func, json={"itens": [item(1)], "pagamentos": [{"metodo": "visa", "valor": 200}]})
    verificar("Funcionario PODE registar vendas (201)", r.status_code == 201, r.text)
    vid_func = r.json()["venda_id"]
    r = client.post(f"/vendas/{vid_func}/anular", headers=func, json={})
    verificar("Funcionario NAO pode anular vendas (403)", r.status_code == 403, r.text)

    total, passou = len(_res), sum(_res)
    print("\n" + "=" * 62)
    print(f"  RESULTADO: {passou}/{total} passos OK")
    print("  🎉 Vendas a funcionar corretamente." if passou == total else f"  ⚠️  {total-passou} passo(s) falharam.")
    print("=" * 62)
    try: os.unlink(db_path)
    except OSError: pass
    sys.exit(0 if passou == total else 1)

if __name__ == "__main__":
    main()