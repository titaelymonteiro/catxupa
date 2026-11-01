"""Alertas automaticos de stock e validade.

- listar_alertas: devolve as listas atuais (para mostrar num painel).
- gerar_alertas: cria notificacoes no sino para cada problema, sem repetir
  (usa `criar_se_ausente`, que ignora chaves ja existentes por ler).
"""
from .medicamento_model import (
    listar_stock_baixo, listar_vencimento_proximo, listar_expirados
)
from .notificacao_model import criar_se_ausente


def listar_alertas(limite_stock: int = 10, dias_validade: int = 30):
    return {
        "stock_baixo": listar_stock_baixo(limite_stock),
        "validade_proxima": listar_vencimento_proximo(dias_validade),
        "expirados": listar_expirados(),
        "limite_stock": limite_stock,
        "dias_validade": dias_validade,
    }


def gerar_alertas(limite_stock: int = 10, dias_validade: int = 30) -> int:
    """Cria notificacoes para os alertas atuais. Devolve quantas foram criadas
    (as repetidas, ainda por ler, sao ignoradas)."""
    novos = 0

    for m in listar_stock_baixo(limite_stock):
        if criar_se_ausente(
            "stock_baixo",
            f"Stock baixo: {m['nome']} ({m['estoque']} unidades)",
            "medicamentos.html",
            f"stock:{m['id']}",
        ):
            novos += 1

    for m in listar_expirados():
        if criar_se_ausente(
            "expirado",
            f"Medicamento EXPIRADO: {m['nome']} (validade {m['validade']})",
            "medicamentos.html",
            f"expirado:{m['id']}",
        ):
            novos += 1

    for m in listar_vencimento_proximo(dias_validade):
        if criar_se_ausente(
            "validade_proxima",
            f"A expirar em breve: {m['nome']} (validade {m['validade']})",
            "medicamentos.html",
            f"validade:{m['id']}",
        ):
            novos += 1

    return novos