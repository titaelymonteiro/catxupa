"""
Teste manual AUTOMATIZADO do programa de FIDELIDADE (pontos).

Regras verificadas: ganha 1 ponto por cada 100 CVE; cada ponto resgatado
vale 5 CVE de desconto; nao se resgata mais do que se tem; anular uma venda
reverte os pontos ganhos e repoe os pontos resgatados.

Usa uma base de dados TEMPORARIA — nao toca na tua farmacia.db.
Correr (na pasta que contem 'backend'):   py testar_fidelidade.py
"""
import os, sys, tempfile
os.environ.setdefault("SECRET_KEY", "chave-de-teste-fidelidade")
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
    print("  TESTE DO PROGRAMA DE FIDELIDADE  —  Farmacia CV")
    print("=" * 62)
    client, db_path = preparar()
    admin = auth(client.post("/login", json={"email": "admin@farmacia.cv", "password": "admin123"}).json()["access_token"])

    def novo_medicamento(nome, preco, estoque=50):
        client.post("/medicamentos", headers=admin, json={
            "nome": nome, "preco": preco, "estoque": estoque, "validade": "2027-12-31", "categoria": "Teste"})
        meds = client.get("/medicamentos", headers=admin).json()
        return max((m for m in meds if m["nome"] == nome), key=lambda m: m["id"])["id"]

    def novo_cliente(email):
        r = client.post("/registar", json={"nome": "Cliente Fid", "email": email, "password": "1234"})
        headers = auth(r.json()["access_token"])
        clientes = client.get("/clientes", headers=admin).json()
        cid = next(c["id"] for c in clientes if c["email"] == email)
        return headers, cid

    def vender(cid, med_id, preco, qtd=1, resgatar=0, metodo="visa"):
        subtotal = round(preco * qtd, 2)
        total_pagar = max(0, round(subtotal - resgatar * 5.0, 2))
        pagamentos = [{"metodo": metodo, "valor": total_pagar}] if total_pagar > 0 else [{"metodo": metodo, "valor": 0.01}]
        return client.post("/vendas", headers=admin, json={
            "cliente": "Cliente Fid", "cliente_id": cid,
            "itens": [{"medicamento_id": med_id, "medicamento_nome": "x", "quantidade": qtd,
                       "preco_unitario": preco, "subtotal": subtotal}],
            "pagamentos": pagamentos, "pontos_resgatados": resgatar})

    def saldo(headers): return client.get("/minha-fidelidade", headers=headers).json()["saldo"]

    titulo("Ganho de pontos")
    h1, c1 = novo_cliente("gan@example.com")
    med500 = novo_medicamento("Med 500", 500.0)
    r = vender(c1, med500, 500.0)
    verificar("Venda de 500 CVE a um cliente (201)", r.status_code == 201, r.text)
    verificar("Ganhou 5 pontos (500 / 100)", saldo(h1) == 5, f"saldo={saldo(h1)}")

    med100 = novo_medicamento("Med 100", 100.0)
    r = client.post("/vendas", headers=admin, json={  # venda SEM cliente
        "itens": [{"medicamento_id": med100, "medicamento_nome": "x", "quantidade": 1, "preco_unitario": 100.0, "subtotal": 100.0}],
        "pagamentos": [{"metodo": "visa", "valor": 100.0}]})
    verificar("Venda sem cliente associado nao gera pontos (mas funciona, 201)", r.status_code == 201, r.text)

    titulo("Resgate de pontos (5 CVE por ponto)")
    r = vender(c1, med100, 100.0, resgatar=4)   # desconto 20 -> paga 80 -> ganha 0
    verificar("Resgatar 4 pontos numa compra de 100 CVE (201)", r.status_code == 201, r.text)
    verificar("Saldo desce 4 (5 - 4 + 0 ganhos = 1)", saldo(h1) == 1, f"saldo={saldo(h1)}")

    r = vender(c1, med100, 100.0, resgatar=999)
    verificar("Resgatar mais pontos do que tem e recusado (400)", r.status_code == 400, r.text)

    r = client.post("/vendas", headers=admin, json={  # resgatar sem cliente
        "itens": [{"medicamento_id": med100, "medicamento_nome": "x", "quantidade": 1, "preco_unitario": 100.0, "subtotal": 100.0}],
        "pagamentos": [{"metodo": "visa", "valor": 100.0}], "pontos_resgatados": 3})
    verificar("Resgatar pontos sem cliente associado e recusado (400)", r.status_code == 400, r.text)

    titulo("Anulacao reverte os pontos")
    h2, c2 = novo_cliente("anu@example.com")
    r = vender(c2, med500, 500.0)      # ganha 5
    vid_ganho = r.json()["venda_id"]
    verificar("Cliente novo ganhou 5 pontos", saldo(h2) == 5, f"saldo={saldo(h2)}")
    client.post(f"/vendas/{vid_ganho}/anular", headers=admin, json={"motivo": None})
    verificar("Anular a venda reverte os pontos ganhos (saldo 0)", saldo(h2) == 0, f"saldo={saldo(h2)}")

    h3, c3 = novo_cliente("res@example.com")
    med1000 = novo_medicamento("Med 1000", 1000.0)
    vender(c3, med1000, 1000.0)        # ganha 10
    r = vender(c3, med100, 100.0, resgatar=5)   # resgata 5 (desconto 25 -> paga 75 -> ganha 0)
    vid_resg = r.json()["venda_id"]
    verificar("Apos resgatar 5, saldo = 10 - 5 = 5", saldo(h3) == 5, f"saldo={saldo(h3)}")
    client.post(f"/vendas/{vid_resg}/anular", headers=admin, json={"motivo": None})
    verificar("Anular a venda repoe os 5 pontos resgatados (saldo 10)", saldo(h3) == 10, f"saldo={saldo(h3)}")

    titulo("Consultas")
    fid = client.get("/minha-fidelidade", headers=h1).json()
    verificar("O historico regista movimentos do tipo 'ganho'", any(h["tipo"] == "ganho" for h in fid["historico"]), str(fid))
    r = client.get(f"/clientes/{c1}/pontos", headers=admin)
    verificar("Staff consegue ver os pontos de um cliente (200)", r.status_code == 200 and "saldo" in r.json(), r.text)

    total, passou = len(_res), sum(_res)
    print("\n" + "=" * 62)
    print(f"  RESULTADO: {passou}/{total} passos OK")
    print("  🎉 Fidelidade a funcionar corretamente." if passou == total else f"  ⚠️  {total-passou} passo(s) falharam.")
    print("=" * 62)
    try: os.unlink(db_path)
    except OSError: pass
    sys.exit(0 if passou == total else 1)

if __name__ == "__main__":
    main()