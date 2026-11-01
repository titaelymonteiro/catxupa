# Como executar a Farmácia CV

Este projeto tem **duas partes**: um **servidor** (backend, em Python) e as
**páginas** (frontend, que se abrem no navegador). As páginas só funcionam com o
servidor ligado — por isso a ordem é: **1) ligar o servidor, 2) abrir as páginas**.

---

## ✅ Antes de começar

Instala o **Python 3.11 ou superior**: https://www.python.org/downloads/
No Windows, durante a instalação, **marca a opção "Add Python to PATH"**.

---

## 🚀 Modo fácil (recomendado)

**Windows:** faz **duplo-clique** em `iniciar.bat`.
**Mac / Linux:** abre um terminal na pasta do projeto e corre `bash iniciar.sh`.

O script faz tudo sozinho (instala o necessário, cria a chave de segurança e liga
o servidor). Quando aparecer a mensagem *"Servidor a arrancar em
http://127.0.0.1:8000"*, faz o passo seguinte.

**Depois:** abre o ficheiro **`frontend/login.html`** no navegador e entra com:
- Email: `admin@farmacia.cv`
- Palavra-passe: `admin123`

Deixa a janela do servidor **aberta** enquanto usas o sistema. Para desligar,
fecha essa janela (ou carrega `Ctrl+C`).

---

## 🔧 Modo manual (se preferires fazer à mão)

Abre um terminal na pasta do projeto e corre, por ordem:

```bash
# 1. Instalar as dependências
pip install -r requirements.txt

# 2. Criar o ficheiro backend/.env com uma chave secreta
#    (só é preciso uma vez). Escreve lá dentro esta linha:
#    SECRET_KEY="qualquer-texto-secreto-aqui"

# 3. Ligar o servidor
python -m uvicorn backend.main:app --reload
```

Depois abre `frontend/login.html` no navegador.

---

## ❓ Problemas comuns

- **"As páginas não fazem nada / não entra"** → o servidor não está ligado.
  Liga-o primeiro (modo fácil ou manual) e só depois abre o `login.html`.
- **"SECRET_KEY não definida"** → falta o ficheiro `backend/.env`. O modo fácil
  cria-o automaticamente; no modo manual, cria-o com a linha do passo 2.
- **Os mapas não aparecem** → é preciso ligação à internet (os mapas e alguns
  estilos vêm da internet).
- **"py não é reconhecido" (Windows)** → o Python não foi adicionado ao PATH.
  Reinstala o Python marcando "Add Python to PATH".

---

## 👤 Contas

- **Administrador** (acesso total): `admin@farmacia.cv` / `admin123`
- **Clientes**: criam a sua própria conta na página "Criar conta".
- **Funcionários**: são criados pelo administrador, na página "Utilizadores".