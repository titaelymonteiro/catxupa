import httpx
import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Pagali (Devem ser preenchidas pelo utilizador)
PAGALI_API_URL = "https://api.pagali.cv/v1"
PAGALI_APP_ID = os.getenv("PAGALI_APP_ID", "O_TEU_APP_ID")
PAGALI_APP_SECRET = os.getenv("PAGALI_APP_SECRET", "O_TEU_APP_SECRET")

async def criar_checkout_pagali(venda_id: int, total: float, cliente_nome: str):
    """
    Simula a criação de um pedido de pagamento no Pagali.
    Retorna o URL para redirecionar o cliente.
    """
    payload = {
        "amount": total,
        "currency": "CVE",
        "description": f"Venda Farmácia CV #{venda_id}",
        "order_id": str(venda_id),
        "return_url": "http://127.0.0.1:5500/frontend/vendas.html?status=sucesso",
        "cancel_url": "http://127.0.0.1:5500/frontend/vendas.html?status=cancelado",
        "metadata": {
            "venda_id": venda_id,
            "cliente": cliente_nome
        }
    }

    # Nota: Em produção, deves enviar os cabeçalhos de autenticação corretos do Pagali
    headers = {
        "Authorization": f"Bearer {PAGALI_APP_SECRET}",
        "Content-Type": "application/json"
    }

    # Aqui simulamos a chamada. Na vida real seria um try/except com httpx.
    # mock_url = f"https://checkout.pagali.cv/p/{venda_id}_mock"
    # return mock_url

    try:
        async with httpx.AsyncClient() as client:
            # Esta URL é fictícia, deve ser confirmada na doc oficial do Pagali
            response = await client.post(f"{PAGALI_API_URL}/checkout", json=payload, headers=headers)
            if response.status_code == 200:
                return response.json().get("payment_url")
            else:
                # Se falhar (ex: sem chaves reais), devolvemos um link de simulação
                return f"https://simular.pagali.cv/pay/{venda_id}?amount={total}"
    except Exception:
        return f"https://simular.pagali.cv/pay/{venda_id}?amount={total}"
