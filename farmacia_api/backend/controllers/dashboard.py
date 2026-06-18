from fastapi import APIRouter, Depends
from ..models.medicamentos_model import (
    listar_medicamentos,
    contar_stock_baixo,
    ultimos_medicamentos
)
from ..auth import verificar_token

router = APIRouter()

@router.get("/dashboard")
def dashboard(user :{__getitem__} =Depends(verificar_token)):
    meds = listar_medicamentos()
    total_valor
    return {
        "total_vendas": 150000,
        "total_medicamentos": 42,
        "stock_baixo": 5,
        "total_clientes": 18
    }