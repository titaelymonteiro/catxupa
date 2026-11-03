"""Testes do backup e restauro da base de dados."""


def test_backup_descarrega_sqlite(client, admin_headers):
    resp = client.get("/backup", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.content.startswith(b"SQLite format 3\x00")
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_restaurar_repoe_dados(client, admin_headers):
    # criar um marcador
    client.post("/clientes", json={"nome": "MarcadorBackup", "telefone": "9",
                                    "email": "m@m.cv", "endereco": "A"}, headers=admin_headers)

    backup = client.get("/backup", headers=admin_headers).content

    # apagar o marcador
    cid = next(c["id"] for c in client.get("/clientes", headers=admin_headers).json()
               if c["nome"] == "MarcadorBackup")
    client.delete(f"/clientes/{cid}", headers=admin_headers)
    assert not any(c["nome"] == "MarcadorBackup"
                   for c in client.get("/clientes", headers=admin_headers).json())

    # restaurar
    resp = client.post("/restaurar",
                       files={"ficheiro": ("bk.db", backup, "application/octet-stream")},
                       headers=admin_headers)
    assert resp.status_code == 200, resp.text
    assert any(c["nome"] == "MarcadorBackup"
               for c in client.get("/clientes", headers=admin_headers).json())


def test_restaurar_ficheiro_invalido(client, admin_headers):
    resp = client.post("/restaurar",
                       files={"ficheiro": ("x.db", b"isto nao e uma base de dados", "application/octet-stream")},
                       headers=admin_headers)
    assert resp.status_code == 400


def test_backup_e_so_admin(client, funcionario_headers):
    assert client.get("/backup", headers=funcionario_headers).status_code == 403


def test_restaurar_e_so_admin(client, funcionario_headers):
    resp = client.post("/restaurar",
                       files={"ficheiro": ("x.db", b"SQLite format 3\x00", "application/octet-stream")},
                       headers=funcionario_headers)
    assert resp.status_code == 403