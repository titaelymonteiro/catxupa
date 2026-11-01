"""Testes de /usuarios — regras de permissão por perfil."""


def test_admin_pode_listar_usuarios(client, admin_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    assert resp.status_code == 200
    assert any(u["email"] == "admin@farmacia.cv" for u in resp.json())


def test_funcionario_nao_pode_listar_usuarios(client, funcionario_headers):
    """/usuarios (listar todos) é restrito a admin."""
    resp = client.get("/usuarios", headers=funcionario_headers)
    assert resp.status_code == 403


def test_criar_usuario_com_email_duplicado_falha(client, admin_headers):
    dados = {
        "nome": "Repetido",
        "email": "repetido@farmacia.cv",
        "password": "1234",
        "perfil": "funcionario",
    }
    primeiro = client.post("/usuarios", json=dados, headers=admin_headers)
    assert primeiro.status_code == 201

    segundo = client.post("/usuarios", json=dados, headers=admin_headers)
    assert segundo.status_code == 400


def test_funcionario_nao_pode_criar_usuarios(client, funcionario_headers):
    resp = client.post(
        "/usuarios",
        json={
            "nome": "X",
            "email": "x@farmacia.cv",
            "password": "1234",
            "perfil": "funcionario",
        },
        headers=funcionario_headers,
    )
    assert resp.status_code == 403


def test_admin_nao_pode_apagar_a_propria_conta(client, admin_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.delete(f"/usuarios/{admin_id}", headers=admin_headers)
    assert resp.status_code == 400


def test_alterar_password_com_password_atual_errada_falha(client, admin_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/password",
        json={"password_atual": "errada", "password_nova": "novaPass123"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_alterar_a_propria_password_com_sucesso(client, admin_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/password",
        json={"password_atual": "admin123", "password_nova": "novaPass123"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    # a password antiga deixa de funcionar
    velho_login = client.post(
        "/login", json={"email": "admin@farmacia.cv", "password": "admin123"}
    )
    assert velho_login.status_code == 401

    # a nova password funciona
    novo_login = client.post(
        "/login", json={"email": "admin@farmacia.cv", "password": "novaPass123"}
    )
    assert novo_login.status_code == 200


def test_funcionario_nao_pode_alterar_password_de_outro(client, admin_headers, funcionario_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/password",
        json={"password_atual": "admin123", "password_nova": "hackeado123"},
        headers=funcionario_headers,
    )
    assert resp.status_code == 403


def test_admin_repoe_password_sem_saber_a_antiga(client, admin_headers):
    dados = {
        "nome": "Vai Esquecer",
        "email": "vaiesquecer@farmacia.cv",
        "password": "1234",
        "perfil": "funcionario",
    }
    client.post("/usuarios", json=dados, headers=admin_headers)
    resp = client.get("/usuarios", headers=admin_headers)
    alvo_id = next(u["id"] for u in resp.json() if u["email"] == "vaiesquecer@farmacia.cv")

    resp = client.put(
        f"/usuarios/{alvo_id}/reset-password",
        json={"password_nova": "novaPasswordSemSaberAntiga"},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    login = client.post(
        "/login", json={"email": "vaiesquecer@farmacia.cv", "password": "novaPasswordSemSaberAntiga"}
    )
    assert login.status_code == 200


def test_reset_password_curta_falha(client, admin_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/reset-password",
        json={"password_nova": "12"},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_reset_password_utilizador_inexistente_falha(client, admin_headers):
    resp = client.put(
        "/usuarios/999999/reset-password",
        json={"password_nova": "qualquercoisa"},
        headers=admin_headers,
    )
    assert resp.status_code == 404


def test_funcionario_nao_pode_repor_password_de_outro(client, admin_headers, funcionario_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/reset-password",
        json={"password_nova": "tentativaFuncionario"},
        headers=funcionario_headers,
    )
    assert resp.status_code == 403


def test_cliente_nao_pode_repor_password(client, admin_headers, cliente_headers):
    resp = client.get("/usuarios", headers=admin_headers)
    admin_id = next(u["id"] for u in resp.json() if u["email"] == "admin@farmacia.cv")

    resp = client.put(
        f"/usuarios/{admin_id}/reset-password",
        json={"password_nova": "tentativaCliente"},
        headers=cliente_headers,
    )
    assert resp.status_code == 403


def test_reset_password_gera_log(client, admin_headers):
    dados = {
        "nome": "Log Reset",
        "email": "logreset@farmacia.cv",
        "password": "1234",
        "perfil": "funcionario",
    }
    client.post("/usuarios", json=dados, headers=admin_headers)
    resp = client.get("/usuarios", headers=admin_headers)
    alvo_id = next(u["id"] for u in resp.json() if u["email"] == "logreset@farmacia.cv")

    client.put(
        f"/usuarios/{alvo_id}/reset-password",
        json={"password_nova": "novaPassword123"},
        headers=admin_headers,
    )

    logs = client.get("/logs", headers=admin_headers).json()
    assert any(
        log["acao"] == "editar" and log["entidade"] == "usuario" and log["entidade_id"] == str(alvo_id)
        for log in logs
    )


def test_reset_password_limpa_bloqueio_de_tentativas(client, admin_headers):
    dados = {
        "nome": "Bloqueado",
        "email": "bloqueado@farmacia.cv",
        "password": "1234",
        "perfil": "funcionario",
    }
    client.post("/usuarios", json=dados, headers=admin_headers)

    for _ in range(5):
        client.post("/login", json={"email": "bloqueado@farmacia.cv", "password": "errada"})

    bloqueado = client.post("/login", json={"email": "bloqueado@farmacia.cv", "password": "1234"})
    assert bloqueado.status_code == 429

    resp = client.get("/usuarios", headers=admin_headers)
    alvo_id = next(u["id"] for u in resp.json() if u["email"] == "bloqueado@farmacia.cv")
    client.put(
        f"/usuarios/{alvo_id}/reset-password",
        json={"password_nova": "novaAposBloqueio"},
        headers=admin_headers,
    )

    login = client.post("/login", json={"email": "bloqueado@farmacia.cv", "password": "novaAposBloqueio"})
    assert login.status_code == 200