#!/usr/bin/env bash
# ============================================================
#   Farmacia CV - Arranque automatico (Mac / Linux)
#   Correr com:   bash iniciar.sh
# ============================================================
cd "$(dirname "$0")" || exit 1

echo
echo "====== Farmacia CV ======"
echo

# 1) Confirmar que o Python esta instalado
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERRO] O Python 3 nao esta instalado."
    echo "Instala-o em https://www.python.org/downloads/ (ou pelo gestor de pacotes)."
    exit 1
fi

# 2) Criar o ambiente virtual (so na primeira vez)
if [ ! -d "venv" ]; then
    echo "A preparar o ambiente pela primeira vez..."
    python3 -m venv venv
fi

# 3) Ativar o ambiente e instalar as dependencias
source venv/bin/activate
echo "A instalar/atualizar as dependencias..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# 4) Criar o ficheiro .env com uma chave secreta (so se nao existir)
if [ ! -f "backend/.env" ]; then
    python -c "import secrets; print('SECRET_KEY=\"'+secrets.token_hex(32)+'\"')" > backend/.env
    echo "Criado backend/.env com uma chave secreta nova."
fi

# 5) Arrancar o servidor
echo
echo "============================================================"
echo "  Servidor a arrancar em: http://127.0.0.1:8000"
echo
echo "  AGORA: abre o ficheiro  frontend/login.html  no navegador."
echo "  Entra com:  admin@farmacia.cv  /  admin123"
echo
echo "  (Deixa este terminal ABERTO enquanto usas o sistema.)"
echo "  (Para desligar, carrega Ctrl+C.)"
echo "============================================================"
echo
python -m uvicorn backend.main:app --reload