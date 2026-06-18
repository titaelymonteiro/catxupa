from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

from .auth.auth import criar_token, verificar_token
from .models.db import init_db, get_connection, hash_password
from .models.medicamento_model import (
    listar_medicamentos, inserir_medicamento, obter_medicamento_por_id,
    atualizar_medicamento, deletar_medicamento,
    contar_stock_baixo, ultimos_medicamentos
)
from .models.usuario_model import (
    listar_usuarios, obter_usuario_por_id, criar_usuario,
    atualizar_usuario, alterar_password, deletar_usuario,
    verificar_password, obter_usuario_por_email
)
from .models.venda_model import (
    criar_venda, listar_vendas, obter_venda, resumo_vendas
)
from .models.cliente_model import (
    listar_clientes, obter_cliente_por_id, criar_cliente,
    atualizar_cliente, deletar_cliente, contar_clientes,
    historico_compras_cliente
)

init_db()

app = FastAPI(title="Farmácia CV API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Modelos ────────────────────────────────────────────────────────────────

class LoginDados(BaseModel):
    email: str
    password: str

class MedicamentoIn(BaseModel):
    nome: str
    preco: float
    estoque: int
    validade: Optional[str] = ""
    categoria: Optional[str] = ""

class UsuarioIn(BaseModel):
    nome: str
    email: str
    password: Optional[str] = None
    perfil: str = "funcionario"

class AlterarPasswordIn(BaseModel):
    password_atual: str
    password_nova: str

class VendaItemIn(BaseModel):
    medicamento_id: int
    medicamento_nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float

class ClienteIn(BaseModel):
    nome: str
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""

class VendaIn(BaseModel):
    cliente: str = "Cliente Geral"
    cliente_id: Optional[int] = None
    itens: List[VendaItemIn]

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.post("/login")
def login(dados: LoginDados):
    user = obter_usuario_por_email(dados.email)
    if not user or not verificar_password(dados.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = criar_token(dados.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "nome": user["nome"],
        "perfil": user["perfil"]
    }

# ─── DASHBOARD ───────────────────────────────────────────────────────────────

@app.get("/dashboard")
def dashboard(user=Depends(verificar_token)):
    meds = listar_medicamentos()
    total_valor = sum(m["preco"] * m["estoque"] for m in meds)
    rv = resumo_vendas()
    return {
        "total_vendas": rv["total_geral"],
        "total_medicamentos": len(meds),
        "stock_baixo": contar_stock_baixo(limite=10),
        "total_clientes": contar_clientes(),
        "vendas_mensais": [v["total"] for v in rv["mensais"]] or [0],
        "ultimos_medicamentos": ultimos_medicamentos(5),
        "user": user["email"]
    }

# ─── MEDICAMENTOS ─────────────────────────────────────────────────────────────

@app.get("/medicamentos")
def listar(user=Depends(verificar_token)):
    return listar_medicamentos()

@app.get("/medicamentos/{id}")
def obter(id: int, user=Depends(verificar_token)):
    med = obter_medicamento_por_id(id)
    if not med:
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    return med

@app.post("/medicamentos", status_code=201)
def criar(med: MedicamentoIn, user=Depends(verificar_token)):
    inserir_medicamento(med.nome, med.preco, med.estoque, med.validade, med.categoria)
    return {"mensagem": "Medicamento criado com sucesso"}

@app.put("/medicamentos/{id}")
def editar(id: int, med: MedicamentoIn, user=Depends(verificar_token)):
    if not obter_medicamento_por_id(id):
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    atualizar_medicamento(id, med.nome, med.preco, med.estoque, med.validade, med.categoria)
    return {"mensagem": "Medicamento atualizado com sucesso"}

@app.delete("/medicamentos/{id}")
def apagar_med(id: int, user=Depends(verificar_token)):
    if not obter_medicamento_por_id(id):
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    deletar_medicamento(id)
    return {"mensagem": "Medicamento removido com sucesso"}

# ─── UTILIZADORES ─────────────────────────────────────────────────────────────

def apenas_admin(user=Depends(verificar_token)):
    u = obter_usuario_por_email(user["email"])
    if not u or u["perfil"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user

@app.get("/usuarios")
def listar_users(user=Depends(apenas_admin)):
    return listar_usuarios()

@app.get("/usuarios/{id}")
def obter_user(id: int, user=Depends(verificar_token)):
    u = obter_usuario_por_id(id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    return u

@app.post("/usuarios", status_code=201)
def criar_user(dados: UsuarioIn, user=Depends(apenas_admin)):
    if not dados.password:
        raise HTTPException(status_code=400, detail="Password obrigatória")
    ok = criar_usuario(dados.nome, dados.email, dados.password, dados.perfil)
    if not ok:
        raise HTTPException(status_code=400, detail="Email já existe")
    return {"mensagem": "Utilizador criado com sucesso"}

@app.put("/usuarios/{id}")
def editar_user(id: int, dados: UsuarioIn, user=Depends(apenas_admin)):
    if not obter_usuario_por_id(id):
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    ok = atualizar_usuario(id, dados.nome, dados.email, dados.perfil)
    if not ok:
        raise HTTPException(status_code=400, detail="Email já existe noutro utilizador")
    return {"mensagem": "Utilizador atualizado"}

@app.delete("/usuarios/{id}")
def apagar_user(id: int, user=Depends(apenas_admin)):
    u = obter_usuario_por_id(id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    u_atual = obter_usuario_por_email(user["email"])
    if u_atual and u_atual["id"] == id:
        raise HTTPException(status_code=400, detail="Não podes apagar a tua própria conta")
    deletar_usuario(id)
    return {"mensagem": "Utilizador removido"}

@app.put("/usuarios/{id}/password")
def mudar_password(id: int, dados: AlterarPasswordIn, user=Depends(verificar_token)):
    u = obter_usuario_por_id(id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    u_completo = obter_usuario_por_email(u["email"])
    if not verificar_password(dados.password_atual, u_completo["password"]):
        raise HTTPException(status_code=400, detail="Password atual incorreta")
    alterar_password(id, dados.password_nova)
    return {"mensagem": "Password alterada com sucesso"}

# ─── VENDAS ───────────────────────────────────────────────────────────────────

@app.get("/vendas")
def listar_v(user=Depends(verificar_token)):
    return listar_vendas()

@app.get("/vendas/resumo")
def resumo_v(user=Depends(verificar_token)):
    return resumo_vendas()

@app.get("/vendas/{id}")
def obter_v(id: int, user=Depends(verificar_token)):
    v = obter_venda(id)
    if not v:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    return v

@app.post("/vendas", status_code=201)
def criar_v(dados: VendaIn, user=Depends(verificar_token)):
    if not dados.itens:
        raise HTTPException(status_code=400, detail="A venda precisa de pelo menos um item")
    # Verificar stock
    for item in dados.itens:
        med = obter_medicamento_por_id(item.medicamento_id)
        if not med:
            raise HTTPException(status_code=404, detail=f"Medicamento '{item.medicamento_nome}' não encontrado")
        if med["estoque"] < item.quantidade:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{item.medicamento_nome}' (disponível: {med['estoque']})")
    itens = [i.dict() for i in dados.itens]
    venda_id = criar_venda(dados.cliente, itens, user["email"])
    return {"mensagem": "Venda registada com sucesso", "venda_id": venda_id}

# ─── CLIENTES ─────────────────────────────────────────────────────────────────

@app.get("/clientes")
def listar_c(user=Depends(verificar_token)):
    return listar_clientes()

@app.get("/clientes/{id}")
def obter_c(id: int, user=Depends(verificar_token)):
    c = obter_cliente_por_id(id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return c

@app.get("/clientes/{id}/historico")
def historico_c(id: int, user=Depends(verificar_token)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return historico_compras_cliente(id)

@app.post("/clientes", status_code=201)
def criar_c(dados: ClienteIn, user=Depends(verificar_token)):
    novo_id = criar_cliente(dados.nome, dados.telefone, dados.email, dados.endereco)
    return {"mensagem": "Cliente criado com sucesso", "id": novo_id}

@app.put("/clientes/{id}")
def editar_c(id: int, dados: ClienteIn, user=Depends(verificar_token)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    atualizar_cliente(id, dados.nome, dados.telefone, dados.email, dados.endereco)
    return {"mensagem": "Cliente atualizado com sucesso"}

@app.delete("/clientes/{id}")
def apagar_c(id: int, user=Depends(verificar_token)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    deletar_cliente(id)
    return {"mensagem": "Cliente removido com sucesso"}
