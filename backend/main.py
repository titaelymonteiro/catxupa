from fastapi import FastAPI, HTTPException, Depends, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv as _csv
import io as _io
import os as _os_bk
import shutil as _shutil
import sqlite3 as _sqlite3
import tempfile as _tempfile
import datetime as _dt_bk
from pydantic import BaseModel
from typing import Optional, List
 
from .auth.auth import criar_token, verificar_token
from .auth.rate_limit import esta_bloqueado, registar_falha, limpar_tentativas, tentativas_restantes
from .models.db import init_db, is_hash_legado
from .models.medicamento_model import (
    listar_medicamentos, inserir_medicamento, obter_medicamento_por_id,
    atualizar_medicamento, deletar_medicamento,
    contar_stock_baixo, ultimos_medicamentos,
    contar_vencimento_proximo, listar_vencimento_proximo
)
from .models.usuario_model import (
    listar_usuarios, obter_usuario_por_id, criar_usuario,
    atualizar_usuario, alterar_password, deletar_usuario,
    verificar_password, obter_usuario_por_email, vincular_cliente
)
from .models.venda_model import (
    criar_venda, listar_vendas, obter_venda, resumo_vendas,
    vendas_por_periodo, top_produtos, vendas_por_utilizador, resumo_pagamentos,
    anular_venda, criar_devolucao, relatorio_margem, auditoria_receitas
)
from .models.cliente_model import (
    listar_clientes, obter_cliente_por_id, criar_cliente,
    atualizar_cliente, deletar_cliente, contar_clientes,
    historico_compras_cliente
)
from .models.log_model import registar_log, listar_logs
from .models.fornecedor_model import (
    inserir_fornecedor, listar_fornecedores, obter_fornecedor_por_id,
    atualizar_fornecedor, deletar_fornecedor, fornecedor_tem_lotes
)
from .models.lote_model import (
    criar_lote, listar_lotes, listar_lotes_por_medicamento,
    obter_lote_por_id, deletar_lote
)
from .models.pedido_model import (
    criar_pedido, listar_pedidos, listar_pedidos_por_cliente, obter_pedido,
    atualizar_estado_pedido, cancelar_pedido_cliente, catalogo_disponivel
)
from .models.notificacao_model import (
    criar_notificacao, listar_notificacoes, contar_nao_lidas,
    marcar_como_lida, marcar_todas_como_lidas
)
from .models.alerta_model import listar_alertas, gerar_alertas
from .models.pontos_model import (
    obter_saldo, listar_historico, calcular_desconto, calcular_pontos_ganhos, VALOR_POR_PONTO
)
 
init_db()
 
app = FastAPI(title="Farmácia CV API", version="2.0.0")
 
import os as _os
 
# Origens permitidas: define CORS_ORIGINS no ambiente (separadas por vírgula)
# em produção. Por omissão "*" para facilitar o desenvolvimento. Como a
# autenticação é por token Bearer (header), NÃO usamos cookies/credenciais,
# por isso allow_credentials=False — o que torna "*" válido nos browsers.
_origins = [o.strip() for o in _os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
# ─── Dependências de autorização ─────────────────────────────────────────────
# Definidas no topo porque são usadas como default em Depends(...), que é
# avaliado no momento do import (antes das rotas mais abaixo).
 
def apenas_admin(user=Depends(verificar_token)):
    u = obter_usuario_por_email(user["email"])
    if not u or u["perfil"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores")
    return user
 
def apenas_staff(user=Depends(verificar_token)):
    """Permite admin e funcionário; bloqueia contas com perfil 'cliente'
    (criadas via /registar) de acederem ao backoffice."""
    u = obter_usuario_por_email(user["email"])
    if not u or u["perfil"] == "cliente":
        raise HTTPException(status_code=403, detail="Acesso restrito a funcionários")
    return user
 
 
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
    preco_custo: Optional[float] = None
    fornecedor_id: Optional[int] = None
    requer_receita: Optional[bool] = False
 
class UsuarioIn(BaseModel):
    nome: str
    email: str
    password: Optional[str] = None
    perfil: str = "funcionario"
 
class AlterarPasswordIn(BaseModel):
    password_atual: str
    password_nova: str

class ResetPasswordIn(BaseModel):
    password_nova: str

class PedidoItemIn(BaseModel):
    medicamento_id: int
    quantidade: int

class PedidoIn(BaseModel):
    itens: List[PedidoItemIn]
    nota: Optional[str] = None
    morada_entrega: Optional[str] = None
    entrega_lat: Optional[float] = None
    entrega_lng: Optional[float] = None
    metodo_pagamento: Optional[str] = None
    cartao_ultimos4: Optional[str] = None

class EstadoPedidoIn(BaseModel):
    estado: str
 
class VendaItemIn(BaseModel):
    medicamento_id: int
    medicamento_nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float
    receita_numero: Optional[str] = None
    receita_medico: Optional[str] = None
 
class PagamentoIn(BaseModel):
    metodo: str  # "cartao24" | "visa"
    valor: float
 
class ClienteIn(BaseModel):
    nome: str
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
 
class VendaIn(BaseModel):
    cliente: str = "Cliente Geral"
    cliente_id: Optional[int] = None
    itens: List[VendaItemIn]
    pagamentos: List[PagamentoIn]
    pontos_resgatados: Optional[int] = 0

class AnularVendaIn(BaseModel):
    motivo: Optional[str] = None

class DevolucaoIn(BaseModel):
    medicamento_id: int
    quantidade: int
    motivo: Optional[str] = None

class FornecedorIn(BaseModel):
    nome: str
    nif: Optional[str] = ""
    telefone: Optional[str] = ""
    email: Optional[str] = ""
    endereco: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class LoteIn(BaseModel):
    medicamento_id: int
    fornecedor_id: Optional[int] = None
    numero_lote: str
    quantidade: int
    validade: str
    preco_custo: Optional[float] = None
 
# ─── AUTH ────────────────────────────────────────────────────────────────────
 
@app.post("/login")
def login(dados: LoginDados):
    if esta_bloqueado(dados.email):
        raise HTTPException(
            status_code=429,
            detail="Demasiadas tentativas falhadas. Tenta novamente daqui a 15 minutos."
        )
    user = obter_usuario_por_email(dados.email)
    if not user or not verificar_password(dados.password, user["password"]):
        registar_falha(dados.email)
        restantes = tentativas_restantes(dados.email)
        if restantes == 0:
            raise HTTPException(
                status_code=429,
                detail="Demasiadas tentativas falhadas. Tenta novamente daqui a 15 minutos."
            )
        raise HTTPException(
            status_code=401,
            detail=f"Credenciais inválidas ({restantes} tentativa(s) restante(s) antes de bloquear)"
        )
    limpar_tentativas(dados.email)
    # Migração transparente: se a password ainda estava em SHA-256 antigo,
    # re-grava no formato seguro (PBKDF2) agora que sabemos a password.
    if is_hash_legado(user["password"]):
        alterar_password(user["id"], dados.password)
    token = criar_token(dados.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "nome": user["nome"],
        "perfil": user["perfil"]
    }
 
@app.post("/registar", status_code=201)
def registar_publico(dados: UsuarioIn):
    if not dados.password:
        raise HTTPException(status_code=400, detail="Password obrigatória")
    if len(dados.password) < 4:
        raise HTTPException(status_code=400, detail="A password deve ter pelo menos 4 caracteres")
    ok = criar_usuario(dados.nome, dados.email, dados.password, "cliente")
    if not ok:
        raise HTTPException(status_code=400, detail="Este email já está registado")

    # Cria o registo de cliente correspondente e liga-o à conta, para que a
    # pessoa consiga ver o seu próprio histórico de compras no portal.
    novo_usuario = obter_usuario_por_email(dados.email)
    cliente_id = criar_cliente(dados.nome, "", dados.email, "")
    vincular_cliente(novo_usuario["id"], cliente_id)

    token = criar_token(dados.email)
    return {
        "mensagem": "Conta criada com sucesso",
        "access_token": token,
        "token_type": "bearer"
    }

# ─── PORTAL DO CLIENTE ────────────────────────────────────────────────────────

@app.get("/minha-conta")
def minha_conta(user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    return {
        "id": atual["id"],
        "nome": atual["nome"],
        "email": atual["email"],
        "perfil": atual["perfil"],
        "tem_historico": atual.get("cliente_id") is not None
    }

@app.get("/minhas-compras")
def minhas_compras(user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual or not atual.get("cliente_id"):
        raise HTTPException(status_code=400, detail="Esta conta não tem histórico de compras associado")
    return historico_compras_cliente(atual["cliente_id"])

@app.get("/minha-fidelidade")
def minha_fidelidade(user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual or not atual.get("cliente_id"):
        raise HTTPException(status_code=400, detail="Esta conta não participa no programa de fidelidade")
    return {
        "saldo": obter_saldo(atual["cliente_id"]),
        "historico": listar_historico(atual["cliente_id"]),
        "valor_por_ponto": VALOR_POR_PONTO
    }

# ─── PEDIDOS ONLINE ─────────────────────────────────────────────────────

@app.get("/catalogo")
def obter_catalogo(user=Depends(verificar_token)):
    """Catalogo simplificado para o cliente ver -- sem expor a quantidade
    exata em stock, so se esta disponivel ou nao."""
    return catalogo_disponivel()

@app.post("/pedidos", status_code=201)
def criar_pedido_v(dados: PedidoIn, user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual or not atual.get("cliente_id"):
        raise HTTPException(status_code=400, detail="Esta conta nao pode fazer pedidos online")

    # Pagamento (simulado): aceita apenas o metodo e os ultimos 4 digitos.
    # NUNCA se recebe nem se guarda o numero completo do cartao ou o CVV.
    metodo = dados.metodo_pagamento
    ultimos4 = dados.cartao_ultimos4
    if metodo is not None:
        if metodo not in ("vinti4", "visa"):
            raise HTTPException(status_code=400, detail="Método de pagamento inválido")
        if not ultimos4 or not (ultimos4.isdigit() and len(ultimos4) == 4):
            raise HTTPException(status_code=400, detail="Dados de cartão inválidos")

    try:
        pedido_id = criar_pedido(
            atual["cliente_id"],
            [item.model_dump() for item in dados.itens],
            dados.nota,
            dados.morada_entrega,
            dados.entrega_lat,
            dados.entrega_lng,
            metodo,
            ultimos4
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    registar_log(user["email"], "criar", "pedido", pedido_id, "Fez um pedido online")
    criar_notificacao(
        "pedido_novo",
        f"Novo pedido online de {atual['nome']} (#{pedido_id})",
        "pedidos.html"
    )
    return {"mensagem": "Pedido enviado com sucesso", "pedido_id": pedido_id}

@app.get("/meus-pedidos")
def meus_pedidos(user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual or not atual.get("cliente_id"):
        raise HTTPException(status_code=400, detail="Esta conta nao tem pedidos associados")
    return listar_pedidos_por_cliente(atual["cliente_id"])

@app.post("/meus-pedidos/{id}/cancelar")
def cancelar_meu_pedido(id: int, user=Depends(verificar_token)):
    atual = obter_usuario_por_email(user["email"])
    if not atual or not atual.get("cliente_id"):
        raise HTTPException(status_code=400, detail="Esta conta nao tem pedidos associados")
    try:
        cancelar_pedido_cliente(id, atual["cliente_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"mensagem": "Pedido cancelado com sucesso"}

@app.get("/pedidos")
def listar_pedidos_v(user=Depends(apenas_staff)):
    return listar_pedidos()

@app.get("/pedidos/{id}")
def obter_pedido_v(id: int, user=Depends(apenas_staff)):
    pedido = obter_pedido(id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    return pedido

@app.put("/pedidos/{id}/estado")
def mudar_estado_pedido(id: int, dados: EstadoPedidoIn, user=Depends(apenas_staff)):
    pedido = obter_pedido(id)
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido nao encontrado")
    try:
        atualizar_estado_pedido(id, dados.estado, user["email"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    registar_log(
        user["email"], "editar", "pedido", id,
        f"Alterou o estado do pedido #{id} para '{dados.estado}'"
    )
    return {"mensagem": f"Pedido atualizado para '{dados.estado}'"}

# ─── NOTIFICAÇÕES (EQUIPA) ────────────────────────────────────────────────────

@app.get("/notificacoes")
def obter_notificacoes(limite: int = 20, user=Depends(apenas_staff)):
    return listar_notificacoes(limite)

@app.get("/notificacoes/contagem")
def obter_contagem_notificacoes(user=Depends(apenas_staff)):
    return {"nao_lidas": contar_nao_lidas()}

@app.put("/notificacoes/{id}/lida")
def marcar_notificacao_lida(id: int, user=Depends(apenas_staff)):
    marcar_como_lida(id)
    return {"mensagem": "Notificação marcada como lida"}

@app.put("/notificacoes/marcar-todas-lidas")
def marcar_todas_notificacoes_lidas(user=Depends(apenas_staff)):
    marcar_todas_como_lidas()
    return {"mensagem": "Todas as notificações marcadas como lidas"}

# ─── ALERTAS (stock / validade) ──────────────────────────────────────────────

@app.get("/alertas")
def obter_alertas(limite_stock: int = 10, dias_validade: int = 30, user=Depends(apenas_staff)):
    return listar_alertas(limite_stock, dias_validade)

@app.post("/alertas/verificar")
def verificar_alertas(limite_stock: int = 10, dias_validade: int = 30, user=Depends(apenas_staff)):
    novos = gerar_alertas(limite_stock, dias_validade)
    return {"novos": novos}

# ─── EXPORTAR (CSV) ───────────────────────────────────────────────────────────

def _csv_resposta(nome_ficheiro: str, cabecalhos: list, linhas: list):
    """Gera uma resposta CSV descarregavel. Usa separador ';' e BOM UTF-8
    para o Excel (em portugues) abrir com colunas e acentos corretos."""
    buf = _io.StringIO()
    escritor = _csv.writer(buf, delimiter=";")
    escritor.writerow(cabecalhos)
    for linha in linhas:
        escritor.writerow(["" if c is None else c for c in linha])
    conteudo = "\ufeff" + buf.getvalue()
    return Response(
        content=conteudo,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nome_ficheiro}"'}
    )

@app.get("/exportar/medicamentos")
def exportar_medicamentos(user=Depends(apenas_staff)):
    linhas = [[m.get("id"), m.get("nome"), m.get("preco"), m.get("estoque"),
               m.get("validade"), m.get("categoria")] for m in listar_medicamentos()]
    return _csv_resposta("medicamentos.csv",
                         ["ID", "Nome", "Preco (CVE)", "Stock", "Validade", "Categoria"], linhas)

@app.get("/exportar/clientes")
def exportar_clientes(user=Depends(apenas_staff)):
    linhas = [[c.get("id"), c.get("nome"), c.get("telefone"), c.get("email"),
               c.get("endereco"), c.get("latitude"), c.get("longitude")] for c in listar_clientes()]
    return _csv_resposta("clientes.csv",
                         ["ID", "Nome", "Telefone", "Email", "Endereco", "Latitude", "Longitude"], linhas)

@app.get("/exportar/fornecedores")
def exportar_fornecedores(user=Depends(apenas_staff)):
    linhas = [[f.get("id"), f.get("nome"), f.get("nif"), f.get("telefone"), f.get("email"),
               f.get("endereco"), f.get("latitude"), f.get("longitude")] for f in listar_fornecedores()]
    return _csv_resposta("fornecedores.csv",
                         ["ID", "Nome", "NIF", "Telefone", "Email", "Endereco", "Latitude", "Longitude"], linhas)

@app.get("/exportar/vendas")
def exportar_vendas(user=Depends(apenas_admin)):
    linhas = [[v.get("id"), v.get("cliente"), v.get("total"),
               1 if v.get("anulada") else 0, v.get("criado_em"), v.get("criado_por")]
              for v in listar_vendas()]
    return _csv_resposta("vendas.csv",
                         ["ID", "Cliente", "Total (CVE)", "Anulada", "Data", "Registada por"], linhas)

@app.get("/exportar/pedidos")
def exportar_pedidos(user=Depends(apenas_staff)):
    linhas = [[p.get("id"), p.get("cliente_nome"), p.get("estado"), p.get("total"),
               p.get("morada_entrega"), p.get("criado_em")] for p in listar_pedidos()]
    return _csv_resposta("pedidos.csv",
                         ["ID", "Cliente", "Estado", "Total (CVE)", "Morada de entrega", "Data"], linhas)

# ─── BACKUP / RESTAURO (só admin) ─────────────────────────────────────────────

@app.get("/backup")
def backup_bd(user=Depends(apenas_admin)):
    """Descarrega uma copia consistente da base de dados (.db)."""
    from .models.db import DB_PATH
    tmp = _tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        origem = _sqlite3.connect(DB_PATH)
        destino = _sqlite3.connect(tmp.name)
        with destino:
            origem.backup(destino)   # copia consistente (API de backup do SQLite)
        origem.close()
        destino.close()
        with open(tmp.name, "rb") as f:
            dados = f.read()
    finally:
        _os_bk.unlink(tmp.name)

    nome = f"farmacia_backup_{_dt_bk.datetime.now():%Y%m%d_%H%M}.db"
    registar_log(user["email"], "backup", "sistema", "-", "Descarregou um backup da base de dados")
    return Response(
        content=dados,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'}
    )

@app.post("/restaurar")
async def restaurar_bd(ficheiro: UploadFile = File(...), user=Depends(apenas_admin)):
    """Substitui a base de dados atual pelo ficheiro enviado. DESTRUTIVO."""
    from .models.db import DB_PATH, init_db
    dados = await ficheiro.read()

    if not dados.startswith(b"SQLite format 3\x00"):
        raise HTTPException(status_code=400, detail="O ficheiro não é uma base de dados SQLite válida.")

    tmp = _tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.write(dados)
    tmp.close()
    try:
        conn = _sqlite3.connect(tmp.name)
        tem_usuarios = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='usuarios'"
        ).fetchone()
        conn.close()
        if not tem_usuarios:
            raise HTTPException(status_code=400,
                                detail="Esta base de dados não parece ser da Farmácia CV (falta a tabela 'usuarios').")
        _shutil.copyfile(tmp.name, DB_PATH)
    finally:
        _os_bk.unlink(tmp.name)

    init_db()  # garante que colunas/migracoes recentes existem
    registar_log(user["email"], "restaurar", "sistema", "-", "Restaurou a base de dados a partir de um backup")
    return {"mensagem": "Base de dados restaurada com sucesso."}

# ─── DASHBOARD ───────────────────────────────────────────────────────────────
 
@app.get("/dashboard")
def dashboard(user=Depends(apenas_staff)):
    meds = listar_medicamentos()
    total_valor = sum(m["preco"] * m["estoque"] for m in meds)
    rv = resumo_vendas()
    return {
        "total_vendas": rv["total_geral"],
        "receita_liquida": rv["receita_liquida"],
        "total_devolvido": rv["total_devolvido"],
        "total_medicamentos": len(meds),
        "stock_baixo": contar_stock_baixo(limite=10),
        "vencimento_proximo": contar_vencimento_proximo(dias=30),
        "total_clientes": contar_clientes(),
        "vendas_mensais": [v["total"] for v in rv["mensais"]] or [0],
        "ultimos_medicamentos": ultimos_medicamentos(5),
        "user": user["email"]
    }

@app.get("/medicamentos/vencimento-proximo")
def medicamentos_vencimento_proximo(dias: int = 30, user=Depends(apenas_staff)):
    return listar_vencimento_proximo(dias)
 
# ─── MEDICAMENTOS ─────────────────────────────────────────────────────────────
 
@app.get("/medicamentos")
def listar(user=Depends(apenas_staff)):
    return listar_medicamentos()
 
@app.get("/medicamentos/{id}")
def obter(id: int, user=Depends(apenas_staff)):
    med = obter_medicamento_por_id(id)
    if not med:
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    return med
 
@app.post("/medicamentos", status_code=201)
def criar(med: MedicamentoIn, user=Depends(apenas_staff)):
    inserir_medicamento(med.nome, med.preco, med.estoque, med.validade, med.categoria, med.preco_custo, med.fornecedor_id, med.requer_receita)
    registar_log(user["email"], "criar", "medicamento", "-", f"Criou medicamento '{med.nome}'")
    return {"mensagem": "Medicamento criado com sucesso"}
 
@app.put("/medicamentos/{id}")
def editar(id: int, med: MedicamentoIn, user=Depends(apenas_staff)):
    if not obter_medicamento_por_id(id):
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    atualizar_medicamento(id, med.nome, med.preco, med.estoque, med.validade, med.categoria, med.preco_custo, med.fornecedor_id, med.requer_receita)
    registar_log(user["email"], "editar", "medicamento", id, f"Editou medicamento '{med.nome}'")
    return {"mensagem": "Medicamento atualizado com sucesso"}
 
@app.delete("/medicamentos/{id}")
def apagar_med(id: int, user=Depends(apenas_staff)):
    med = obter_medicamento_por_id(id)
    if not med:
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    deletar_medicamento(id)
    registar_log(user["email"], "apagar", "medicamento", id, f"Apagou medicamento '{med['nome']}'")
    return {"mensagem": "Medicamento removido com sucesso"}
 
# ─── FORNECEDORES ─────────────────────────────────────────────────────────────

@app.get("/fornecedores")
def listar_forn(user=Depends(apenas_staff)):
    return listar_fornecedores()

@app.get("/fornecedores/{id}")
def obter_forn(id: int, user=Depends(apenas_staff)):
    forn = obter_fornecedor_por_id(id)
    if not forn:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    return forn

@app.post("/fornecedores", status_code=201)
def criar_forn(forn: FornecedorIn, user=Depends(apenas_staff)):
    inserir_fornecedor(forn.nome, forn.nif, forn.telefone, forn.email, forn.endereco,
                       forn.latitude, forn.longitude)
    registar_log(user["email"], "criar", "fornecedor", "-", f"Criou fornecedor '{forn.nome}'")
    return {"mensagem": "Fornecedor criado com sucesso"}

@app.put("/fornecedores/{id}")
def editar_forn(id: int, forn: FornecedorIn, user=Depends(apenas_staff)):
    if not obter_fornecedor_por_id(id):
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    atualizar_fornecedor(id, forn.nome, forn.nif, forn.telefone, forn.email, forn.endereco,
                         forn.latitude, forn.longitude)
    registar_log(user["email"], "editar", "fornecedor", id, f"Editou fornecedor '{forn.nome}'")
    return {"mensagem": "Fornecedor atualizado com sucesso"}

@app.delete("/fornecedores/{id}")
def apagar_forn(id: int, user=Depends(apenas_staff)):
    forn = obter_fornecedor_por_id(id)
    if not forn:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    if fornecedor_tem_lotes(id):
        raise HTTPException(status_code=400, detail="Não é possível apagar: existem lotes associados a este fornecedor")
    deletar_fornecedor(id)
    registar_log(user["email"], "apagar", "fornecedor", id, f"Apagou fornecedor '{forn['nome']}'")
    return {"mensagem": "Fornecedor removido com sucesso"}

# ─── LOTES ──────────────────────────────────────────────────────────────────

@app.get("/lotes")
def listar_lts(user=Depends(apenas_staff)):
    return listar_lotes()

@app.get("/lotes/{id}")
def obter_lt(id: int, user=Depends(apenas_staff)):
    lote = obter_lote_por_id(id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    return lote

@app.get("/medicamentos/{id}/lotes")
def listar_lts_do_medicamento(id: int, user=Depends(apenas_staff)):
    if not obter_medicamento_por_id(id):
        raise HTTPException(status_code=404, detail="Medicamento não encontrado")
    return listar_lotes_por_medicamento(id)

@app.post("/lotes", status_code=201)
def criar_lt(lote: LoteIn, user=Depends(apenas_staff)):
    try:
        lote_id = criar_lote(
            lote.medicamento_id, lote.fornecedor_id, lote.numero_lote,
            lote.quantidade, lote.validade, lote.preco_custo, user["email"]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    registar_log(
        user["email"], "criar", "lote", lote_id,
        f"Registou lote '{lote.numero_lote}' ({lote.quantidade} un.) — repõe stock"
    )
    return {"mensagem": "Lote registado e stock atualizado com sucesso", "lote_id": lote_id}

@app.delete("/lotes/{id}")
def apagar_lt(id: int, user=Depends(apenas_staff)):
    lote = obter_lote_por_id(id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote não encontrado")
    deletar_lote(id)
    registar_log(
        user["email"], "apagar", "lote", id,
        f"Apagou lote '{lote['numero_lote']}' — desconta {lote['quantidade']} un. do stock"
    )
    return {"mensagem": "Lote removido e stock ajustado com sucesso"}

# ─── UTILIZADORES ─────────────────────────────────────────────────────────────
 
@app.get("/usuarios")
def listar_users(user=Depends(apenas_admin)):
    return listar_usuarios()
 
@app.get("/usuarios/{id}")
def obter_user(id: int, user=Depends(apenas_staff)):
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
    registar_log(user["email"], "criar", "usuario", "-", f"Criou utilizador '{dados.nome}' ({dados.email})")
    return {"mensagem": "Utilizador criado com sucesso"}
 
@app.put("/usuarios/{id}")
def editar_user(id: int, dados: UsuarioIn, user=Depends(apenas_admin)):
    if not obter_usuario_por_id(id):
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    ok = atualizar_usuario(id, dados.nome, dados.email, dados.perfil)
    if not ok:
        raise HTTPException(status_code=400, detail="Email já existe noutro utilizador")
    registar_log(user["email"], "editar", "usuario", id, f"Editou utilizador '{dados.nome}'")
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
    registar_log(user["email"], "apagar", "usuario", id, f"Apagou utilizador '{u['nome']}'")
    return {"mensagem": "Utilizador removido"}
 
@app.put("/usuarios/{id}/password")
def mudar_password(id: int, dados: AlterarPasswordIn, user=Depends(verificar_token)):
    u = obter_usuario_por_id(id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilizador não encontrado")
    # Só o próprio utilizador (ou um admin) pode alterar a password.
    atual = obter_usuario_por_email(user["email"])
    if not atual or (atual["id"] != id and atual["perfil"] != "admin"):
        raise HTTPException(status_code=403, detail="Só podes alterar a tua própria password")
    u_completo = obter_usuario_por_email(u["email"])
    if not verificar_password(dados.password_atual, u_completo["password"]):
        raise HTTPException(status_code=400, detail="Password atual incorreta")
    alterar_password(id, dados.password_nova)
    return {"mensagem": "Password alterada com sucesso"}

@app.put("/usuarios/{id}/reset-password")
def repor_password(id: int, dados: ResetPasswordIn, user=Depends(apenas_admin)):
    """Permite a um admin repor a password de qualquer utilizador sem
    precisar de saber a password atual — para quando alguem se esquece
    e nao ha servidor de email configurado para um fluxo automatico."""
    u = obter_usuario_por_id(id)
    if not u:
        raise HTTPException(status_code=404, detail="Utilizador nao encontrado")
    if len(dados.password_nova) < 4:
        raise HTTPException(status_code=400, detail="A password deve ter pelo menos 4 caracteres")
    alterar_password(id, dados.password_nova)
    limpar_tentativas(u["email"])
    registar_log(
        user["email"], "editar", "usuario", id,
        f"Repos a password de '{u['email']}' (reposicao de administrador)"
    )
    return {"mensagem": "Password reposta com sucesso"}
 
# ─── VENDAS ───────────────────────────────────────────────────────────────────
 
@app.get("/vendas")
def listar_v(user=Depends(apenas_staff)):
    return listar_vendas()
 
@app.get("/vendas/resumo")
def resumo_v(user=Depends(apenas_staff)):
    return resumo_vendas()
 
@app.get("/vendas/{id}")
def obter_v(id: int, user=Depends(apenas_staff)):
    v = obter_venda(id)
    if not v:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    return v
 
@app.post("/vendas", status_code=201)
def criar_v(dados: VendaIn, user=Depends(apenas_staff)):
    if not dados.itens:
        raise HTTPException(status_code=400, detail="A venda precisa de pelo menos um item")
    if not dados.pagamentos:
        raise HTTPException(status_code=400, detail="A venda precisa de pelo menos uma forma de pagamento")
 
    # Construir os itens com preços vindos da BASE DE DADOS (nunca do cliente).
    # O browser só decide o medicamento e a quantidade; preço, subtotal e nome
    # são sempre recalculados no servidor para não poderem ser falsificados.
    itens = []
    for item in dados.itens:
        if item.quantidade <= 0:
            raise HTTPException(status_code=400, detail="A quantidade tem de ser positiva")
        med = obter_medicamento_por_id(item.medicamento_id)
        if not med:
            raise HTTPException(status_code=404, detail=f"Medicamento '{item.medicamento_nome}' não encontrado")
        if med["estoque"] < item.quantidade:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{med['nome']}' (disponível: {med['estoque']})")
        preco = med["preco"]
        subtotal = round(preco * item.quantidade, 2)
        itens.append({
            "medicamento_id": med["id"],
            "medicamento_nome": med["nome"],
            "quantidade": item.quantidade,
            "preco_unitario": preco,
            "subtotal": subtotal,
            "receita_numero": item.receita_numero,
            "receita_medico": item.receita_medico,
        })
 
    total_itens = round(sum(i["subtotal"] for i in itens), 2)

    # Resgate de pontos de fidelidade -- desconta do total antes de validar
    # o pagamento.
    desconto_pontos = 0.0
    pontos_resgatados = dados.pontos_resgatados or 0
    if pontos_resgatados < 0:
        raise HTTPException(status_code=400, detail="Numero de pontos invalido")
    if pontos_resgatados > 0:
        if not dados.cliente_id:
            raise HTTPException(status_code=400, detail="E preciso associar um cliente para resgatar pontos")
        saldo_atual = obter_saldo(dados.cliente_id)
        if pontos_resgatados > saldo_atual:
            raise HTTPException(
                status_code=400,
                detail=f"Saldo de pontos insuficiente (tem {saldo_atual}, tentou usar {pontos_resgatados})"
            )
        desconto_pontos = calcular_desconto(pontos_resgatados)

    total_a_pagar = round(max(0, total_itens - desconto_pontos), 2)

    # Verificar que a soma dos pagamentos corresponde ao total calculado no servidor
    METODOS_VALIDOS = {"cartao24", "visa"}
    for p in dados.pagamentos:
        if p.metodo not in METODOS_VALIDOS:
            raise HTTPException(status_code=400, detail=f"Forma de pagamento invalida: '{p.metodo}'")
        if p.valor <= 0:
            raise HTTPException(status_code=400, detail="O valor de cada pagamento tem de ser positivo")

    total_recebido = round(sum(p.valor for p in dados.pagamentos), 2)
    total_nao_dinheiro = round(sum(p.valor for p in dados.pagamentos if p.metodo != "dinheiro"), 2)

    # So o dinheiro pode exceder o total (gera troco). Cartao/transferencia nao.
    if total_nao_dinheiro > total_a_pagar + 0.01:
        raise HTTPException(
            status_code=400,
            detail=f"O valor pago ({total_nao_dinheiro} CVE) excede o total da venda ({total_a_pagar} CVE)"
        )
    if total_recebido < total_a_pagar - 0.01:
        falta = round(total_a_pagar - total_recebido, 2)
        raise HTTPException(
            status_code=400,
            detail=f"Falta pagar {falta} CVE (recebido {total_recebido} de {total_a_pagar} CVE)"
        )

    troco = round(total_recebido - total_a_pagar, 2)
 
    # Pagamentos a registar: somam exatamente o total da venda (o troco é
    # descontado do dinheiro), para os relatórios não contarem o troco.
    restante_troco = troco
    pagamentos = []
    for p in dados.pagamentos:
        valor = p.valor
        if p.metodo == "dinheiro" and restante_troco > 0:
            reduz = min(valor, restante_troco)
            valor = round(valor - reduz, 2)
            restante_troco = round(restante_troco - reduz, 2)
        if valor > 0:
            pagamentos.append({"metodo": p.metodo, "valor": valor})
 
    try:
        venda_id = criar_venda(
            dados.cliente, itens, user["email"], dados.cliente_id,
            pagamentos, valor_recebido=total_recebido, troco=troco,
            pontos_resgatados=pontos_resgatados
        )
    except ValueError as e:
        # Stock esgotou entre a verificação e a gravação (corrida concorrente)
        raise HTTPException(status_code=400, detail=str(e))
    registar_log(user["email"], "criar", "venda", venda_id, f"Registou venda para '{dados.cliente}'")
    return {"mensagem": "Venda registada com sucesso", "venda_id": venda_id, "troco": troco}

@app.post("/vendas/{id}/anular")
def anular_v(id: int, dados: AnularVendaIn, user=Depends(apenas_admin)):
    venda = obter_venda(id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    try:
        anular_venda(id, user["email"], dados.motivo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    registar_log(
        user["email"], "anular", "venda", id,
        f"Anulou a venda #{id} de '{venda['cliente']}'"
        + (f" — motivo: {dados.motivo}" if dados.motivo else "")
    )
    return {"mensagem": "Venda anulada e stock reposto com sucesso"}

@app.post("/vendas/{id}/devolucao")
def devolver_item(id: int, dados: DevolucaoIn, user=Depends(apenas_staff)):
    venda = obter_venda(id)
    if not venda:
        raise HTTPException(status_code=404, detail="Venda não encontrada")
    try:
        res = criar_devolucao(id, dados.medicamento_id, dados.quantidade, user["email"], dados.motivo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    registar_log(
        user["email"], "devolucao", "venda", id,
        f"Devolveu {res['quantidade']}× {res['medicamento_nome']} da venda #{id} ({res['valor']} CVE)"
        + (f" — motivo: {dados.motivo}" if dados.motivo else "")
    )
    return {"mensagem": "Devolução registada e stock reposto", **res}
 
# ─── CLIENTES ─────────────────────────────────────────────────────────────────
 
@app.get("/clientes")
def listar_c(user=Depends(apenas_staff)):
    return listar_clientes()
 
@app.get("/clientes/{id}")
def obter_c(id: int, user=Depends(apenas_staff)):
    c = obter_cliente_por_id(id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return c
 
@app.get("/clientes/{id}/historico")
def historico_c(id: int, user=Depends(apenas_staff)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return historico_compras_cliente(id)

@app.get("/clientes/{id}/pontos")
def pontos_cliente_v(id: int, user=Depends(apenas_staff)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return {"saldo": obter_saldo(id), "historico": listar_historico(id)}
 
@app.post("/clientes", status_code=201)
def criar_c(dados: ClienteIn, user=Depends(apenas_staff)):
    novo_id = criar_cliente(dados.nome, dados.telefone, dados.email, dados.endereco,
                            dados.latitude, dados.longitude)
    registar_log(user["email"], "criar", "cliente", novo_id, f"Criou cliente '{dados.nome}'")
    return {"mensagem": "Cliente criado com sucesso", "id": novo_id}
 
@app.put("/clientes/{id}")
def editar_c(id: int, dados: ClienteIn, user=Depends(apenas_staff)):
    if not obter_cliente_por_id(id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    atualizar_cliente(id, dados.nome, dados.telefone, dados.email, dados.endereco,
                      dados.latitude, dados.longitude)
    registar_log(user["email"], "editar", "cliente", id, f"Editou cliente '{dados.nome}'")
    return {"mensagem": "Cliente atualizado com sucesso"}
 
@app.delete("/clientes/{id}")
def apagar_c(id: int, user=Depends(apenas_staff)):
    c = obter_cliente_por_id(id)
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    deletar_cliente(id)
    registar_log(user["email"], "apagar", "cliente", id, f"Apagou cliente '{c['nome']}'")
    return {"mensagem": "Cliente removido com sucesso"}
 
# ─── RELATÓRIOS ───────────────────────────────────────────────────────────────
 
@app.get("/relatorios/vendas")
def relatorio_vendas(inicio: str, fim: str, user=Depends(apenas_staff)):
    return vendas_por_periodo(inicio, fim)
 
@app.get("/relatorios/top-produtos")
def relatorio_top_produtos(inicio: str = None, fim: str = None, user=Depends(apenas_staff)):
    return top_produtos(inicio, fim)
 
@app.get("/relatorios/utilizadores")
def relatorio_utilizadores(inicio: str = None, fim: str = None, user=Depends(apenas_staff)):
    return vendas_por_utilizador(inicio, fim)
 
@app.get("/relatorios/pagamentos")
def relatorio_pagamentos(inicio: str = None, fim: str = None, user=Depends(apenas_staff)):
    return resumo_pagamentos(inicio, fim)

@app.get("/relatorios/margem")
def relatorio_margem_v(inicio: str = None, fim: str = None, user=Depends(apenas_admin)):
    return relatorio_margem(inicio, fim)

@app.get("/relatorios/receitas")
def relatorio_receitas_v(inicio: str = None, fim: str = None, user=Depends(apenas_admin)):
    """Auditoria de vendas de medicamentos que exigem receita médica."""
    return auditoria_receitas(inicio, fim)
 
# ─── LOG DE ATIVIDADE ──────────────────────────────────────────────────────────
 
@app.get("/logs")
def obter_logs(limite: int = 100, user=Depends(apenas_admin)):
    return listar_logs(limite)