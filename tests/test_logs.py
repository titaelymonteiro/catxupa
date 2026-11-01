"""Testes de /logs (log de auditoria)."""
from conftest import criar_medicamento


def test_logs_vazio_no_inicio(client, admin_headers):
    resp = client.get("/logs", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_criar_medicamento_gera_log(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="Medicamento Auditado")

    resp = client.get("/logs", headers=admin_headers)
    assert resp.status_code == 200
    logs = resp.json()
    assert any(
        log["acao"] == "criar"
        and log["entidade"] == "medicamento"
        and "Medicamento Auditado" in log["descricao"]
        for log in logs
    )


def test_editar_e_apagar_medicamento_geram_logs(client, admin_headers):
    med_id = criar_medicamento(client, admin_headers, nome="Medicamento Editavel")

    client.put(
        f"/medicamentos/{med_id}",
        json={"nome": "Medicamento Editavel", "preco": 200.0, "estoque": 5},
        headers=admin_headers,
    )
    client.delete(f"/medicamentos/{med_id}", headers=admin_headers)

    logs = client.get("/logs", headers=admin_headers).json()
    acoes = [(log["acao"], log["entidade"]) for log in logs]
    assert ("editar", "medicamento") in acoes
    assert ("apagar", "medicamento") in acoes


def test_log_regista_o_email_de_quem_fez_a_acao(client, admin_headers):
    criar_medicamento(client, admin_headers, nome="Rastreavel")

    logs = client.get("/logs", headers=admin_headers).json()
    assert any(log["usuario_email"] == "admin@farmacia.cv" for log in logs)


def test_logs_respeitam_o_limite(client, admin_headers):
    for i in range(5):
        criar_medicamento(client, admin_headers, nome=f"Medicamento {i}")

    resp = client.get("/logs", params={"limite": 2}, headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_logs_restritos_a_admin(client, funcionario_headers):
    resp = client.get("/logs", headers=funcionario_headers)
    assert resp.status_code == 403


def test_logs_sem_autenticacao_falha(client):
    resp = client.get("/logs")
    assert resp.status_code in (401, 403)