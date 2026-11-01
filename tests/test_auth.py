"""Testes de /login e /registar."""


def test_login_com_credenciais_corretas(client):
    resp = client.post(
        "/login",
        json={"email": "admin@farmacia.cv", "password": "admin123"},
    )
    assert resp.status_code == 200
    dados = resp.json()
    assert "access_token" in dados
    assert dados["token_type"] == "bearer"
    assert dados["perfil"] == "admin"


def test_login_com_password_errada(client):
    resp = client.post(
        "/login",
        json={"email": "admin@farmacia.cv", "password": "password-errada"},
    )
    assert resp.status_code == 401


def test_login_com_email_inexistente(client):
    resp = client.post(
        "/login",
        json={"email": "ninguem@farmacia.cv", "password": "qualquer"},
    )
    assert resp.status_code == 401


def test_registar_conta_nova_devolve_token(client):
    resp = client.post(
        "/registar",
        json={
            "nome": "Novo Cliente",
            "email": "novo.cliente@example.com",
            "password": "1234",
        },
    )
    assert resp.status_code == 201
    assert "access_token" in resp.json()


def test_registar_email_duplicado_falha(client):
    dados = {
        "nome": "Duplicado",
        "email": "duplicado@example.com",
        "password": "1234",
    }
    primeiro = client.post("/registar", json=dados)
    assert primeiro.status_code == 201

    segundo = client.post("/registar", json=dados)
    assert segundo.status_code == 400


def test_registar_password_curta_falha(client):
    resp = client.post(
        "/registar",
        json={"nome": "X", "email": "curta@example.com", "password": "12"},
    )
    assert resp.status_code == 400


def test_conta_registada_e_perfil_cliente_nao_acede_ao_backoffice(client, cliente_headers):
    """Contas criadas via /registar ficam com perfil 'cliente' e não podem
    entrar no backoffice (dashboard, medicamentos, etc.)."""
    resp = client.get("/dashboard", headers=cliente_headers)
    assert resp.status_code == 403


def test_rota_protegida_sem_token_falha(client):
    resp = client.get("/dashboard")
    assert resp.status_code in (401, 403)


def test_rota_protegida_com_token_invalido_falha(client):
    resp = client.get(
        "/dashboard", headers={"Authorization": "Bearer token-invalido"}
    )
    assert resp.status_code == 401


def test_registar_cria_registo_de_cliente_vinculado(client, admin_headers):
    resp = client.post(
        "/registar",
        json={"nome": "Cliente Vinculado", "email": "vinculado@example.com", "password": "1234"},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    conta = client.get("/minha-conta", headers={"Authorization": f"Bearer {token}"})
    assert conta.status_code == 200
    assert conta.json()["tem_historico"] is True

    # o registo de cliente correspondente deve existir e aparecer para o staff
    clientes = client.get("/clientes", headers=admin_headers).json()
    assert any(c["nome"] == "Cliente Vinculado" and c["email"] == "vinculado@example.com" for c in clientes)


def test_minha_conta_devolve_dados_proprios(client, cliente_headers):
    resp = client.get("/minha-conta", headers=cliente_headers)
    assert resp.status_code == 200
    dados = resp.json()
    assert dados["email"] == "cliente@example.com"
    assert dados["perfil"] == "cliente"


def test_minha_conta_exige_autenticacao(client):
    resp = client.get("/minha-conta")
    assert resp.status_code in (401, 403)


def test_minhas_compras_vazio_sem_historico(client, cliente_headers):
    resp = client.get("/minhas-compras", headers=cliente_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_minhas_compras_reflete_venda_real(client, admin_headers):
    from conftest import criar_medicamento

    # cria uma conta cliente vinculada
    registo = client.post(
        "/registar",
        json={"nome": "Compradora Real", "email": "compradora@example.com", "password": "1234"},
    )
    token_cliente = registo.json()["access_token"]

    # descobre o cliente_id criado para essa conta, para o staff poder associar a venda
    clientes = client.get("/clientes", headers=admin_headers).json()
    cliente_id = next(c["id"] for c in clientes if c["email"] == "compradora@example.com")

    med_id = criar_medicamento(client, admin_headers, preco=100.0, estoque=10)
    venda = client.post(
        "/vendas",
        json={
            "cliente": "Compradora Real",
            "cliente_id": cliente_id,
            "itens": [{
                "medicamento_id": med_id,
                "medicamento_nome": "Medicamento de Teste",
                "quantidade": 2,
                "preco_unitario": 100.0,
                "subtotal": 200.0,
            }],
            "pagamentos": [{"metodo": "visa", "valor": 200.0}],
        },
        headers=admin_headers,
    )
    assert venda.status_code == 201

    resp = client.get("/minhas-compras", headers={"Authorization": f"Bearer {token_cliente}"})
    assert resp.status_code == 200
    compras = resp.json()
    assert len(compras) == 1
    assert compras[0]["total"] == 200.0


def test_minhas_compras_exige_autenticacao(client):
    resp = client.get("/minhas-compras")
    assert resp.status_code in (401, 403)


def test_login_bloqueia_apos_varias_tentativas_falhadas(client):
    for _ in range(5):
        resp = client.post(
            "/login", json={"email": "bloqueio@teste.com", "password": "errada"}
        )
        assert resp.status_code in (401, 429)

    # a 6ª tentativa deve estar bloqueada, mesmo com a password certa
    resp = client.post(
        "/login", json={"email": "bloqueio@teste.com", "password": "qualquer"}
    )
    assert resp.status_code == 429


def test_login_com_sucesso_limpa_tentativas_falhadas(client):
    client.post(
        "/registar",
        json={"nome": "Limpa Tentativas", "email": "limpa@teste.com", "password": "1234"},
    )

    # duas tentativas falhadas
    client.post("/login", json={"email": "limpa@teste.com", "password": "errada1"})
    client.post("/login", json={"email": "limpa@teste.com", "password": "errada2"})

    # login com sucesso deve limpar o contador
    resp = client.post("/login", json={"email": "limpa@teste.com", "password": "1234"})
    assert resp.status_code == 200

    # confirma que o contador foi mesmo limpo: mais tentativas falhadas nao bloqueiam de imediato
    for _ in range(3):
        resp = client.post("/login", json={"email": "limpa@teste.com", "password": "errada"})
        assert resp.status_code == 401  # ainda nao bloqueado


def test_login_bloqueio_e_isolado_por_email(client):
    for _ in range(5):
        client.post("/login", json={"email": "vitima1@teste.com", "password": "errada"})

    # outro email nao deve estar bloqueado
    resp = client.post(
        "/login", json={"email": "vitima2@teste.com", "password": "errada"}
    )
    assert resp.status_code == 401  # nao 429