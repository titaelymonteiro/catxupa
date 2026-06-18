from ..models.medicamento_model import (
    inserir_medicamento,
    listar_medicamentos,
    obter_medicamento_por_id,
    atualizar_medicamento,
    deletar_medicamento
)

def criar_medicamento(dados: dict):
    inserir_medicamento(
        dados["nome"],
        float(dados["preco"]),
        int(dados["estoque"]),
        dados.get("validade", ""),
        dados.get("categoria", "")
    )
    return {"mensagem": "Medicamento criado com sucesso"}

def obter_medicamentos():
    return listar_medicamentos()

def obter_medicamento(id: int):
    med = obter_medicamento_por_id(id)
    if not med:
        return None
    return med

def editar_medicamento(id: int, dados: dict):
    atualizar_medicamento(
        id,
        dados["nome"],
        float(dados["preco"]),
        int(dados["estoque"]),
        dados.get("validade", ""),
        dados.get("categoria", "")
    )
    return {"mensagem": "Medicamento atualizado com sucesso"}

def remover_medicamento(id: int):
    deletar_medicamento(id)
    return {"mensagem": "Medicamento removido com sucesso"}
