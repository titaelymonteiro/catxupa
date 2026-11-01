@echo off
REM ============================================================
REM   Farmacia CV - Arranque automatico (Windows)
REM   Basta fazer duplo-clique neste ficheiro.
REM ============================================================
title Farmacia CV - Servidor
cd /d "%~dp0"

echo.
echo ====== Farmacia CV ======
echo.

REM 1) Confirmar que o Python esta instalado
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Python nao esta instalado.
    echo Instala o Python em https://www.python.org/downloads/
    echo Ao instalar, marca a opcao "Add Python to PATH".
    pause
    exit /b
)

REM 2) Criar o ambiente virtual (so na primeira vez)
if not exist "venv" (
    echo A preparar o ambiente pela primeira vez...
    py -m venv venv
)

REM 3) Ativar o ambiente e instalar as dependencias
call venv\Scripts\activate.bat
echo A instalar/atualizar as dependencias...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM 4) Criar o ficheiro .env com uma chave secreta (so se nao existir)
if not exist "backend\.env" (
    python -c "import secrets; print('SECRET_KEY=\"'+secrets.token_hex(32)+'\"')" > backend\.env
    echo Criado backend\.env com uma chave secreta nova.
)

REM 5) Arrancar o servidor
echo.
echo ============================================================
echo   Servidor a arrancar em: http://127.0.0.1:8000
echo.
echo   AGORA: abre o ficheiro  frontend\login.html  no navegador.
echo   Entra com:  admin@farmacia.cv  /  admin123
echo.
echo   (Deixa esta janela ABERTA enquanto usas o sistema.)
echo   (Para desligar, fecha esta janela ou carrega Ctrl+C.)
echo ============================================================
echo.
python -m uvicorn backend.main:app --reload

pause