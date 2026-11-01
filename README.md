# 💊 Farmácia CV — Sistema de Gestão de Farmácia

Sistema completo de gestão para uma farmácia, com **API REST em FastAPI**, base de
dados **SQLite** e um **frontend em HTML + Bootstrap + JavaScript**. Cobre todo o
ciclo do negócio: stock e lotes, vendas com fidelidade e devoluções, encomendas
online, clientes e fornecedores, relatórios, alertas automáticos, mapas,
exportação de dados e cópias de segurança.

> Projeto desenvolvido como Trabalho de Conclusão de Curso (TCC).
> **174 testes automáticos** (`pytest`), todos a passar.

---

## Índice

- [Funcionalidades](#funcionalidades)
- [Tecnologias](#tecnologias)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Instalação e execução](#instalação-e-execução)
- [Perfis de utilizador](#perfis-de-utilizador)
- [Testes](#testes)
- [Notas de configuração](#notas-de-configuração)

---

## Funcionalidades

**Stock e produtos**
- Gestão de medicamentos (CRUD, preço, stock, validade, categoria)
- Lotes com validade e preço de custo (entradas de mercadoria)
- Alertas automáticos de **stock baixo**, **validade próxima** e **expirados**,
  com notificações no sino da aplicação

**Vendas (POS)**
- Registo de vendas com múltiplos itens e pagamentos (Cartão 24 / Visa)
- Programa de **fidelidade** (ganho e resgate de pontos)
- **Anulação** de vendas com reposição de stock
- **Devoluções/trocas** parciais por item, com reposição de stock
- Recibo imprimível

**Encomendas online**
- Portal do cliente com catálogo e carrinho
- Estados da encomenda (pendente → confirmado → pronto → concluído / cancelado)
- **Morada de entrega** com marcação no mapa
- Talão imprimível (staff e cliente)

**Clientes e fornecedores**
- CRUD completo, com **localização no mapa** (coordenadas e endereço)

**Gestão e análise**
- Dashboard com estatísticas e **receita líquida** (vendas − devoluções)
- Relatórios (vendas por período, top produtos, margem, pagamentos, receitas)
- Log de auditoria de todas as operações sensíveis
- **Exportação** de listas para CSV (Excel)
- **Backup e restauro** da base de dados (só administrador)

**Segurança**
- Autenticação por **JWT**, com três perfis (admin, funcionário, cliente)
- Limitação de tentativas de login (*rate limiting*)
- Segredos em ficheiro `.env` (fora do controlo de versões)

---

## Tecnologias

| Camada | Tecnologias |
|---|---|
| Backend | Python, FastAPI, Uvicorn, PyJWT, Pydantic |
| Base de dados | SQLite |
| Frontend | HTML, Bootstrap, JavaScript (*vanilla*), Leaflet + OpenStreetMap (mapas) |
| Testes | pytest, httpx |

---

## Estrutura do projeto

```
farmacia_api/
├── backend/
│   ├── main.py                  ← Aplicação FastAPI (todas as rotas da API)
│   ├── .env                     ← Segredos locais (NÃO versionado)
│   ├── .env.example             ← Modelo do .env
│   ├── auth/
│   │   ├── auth.py              ← Criação/verificação de JWT
│   │   └── rate_limit.py        ← Limitação de tentativas de login
│   └── models/
│       ├── db.py                ← Ligação SQLite, criação de tabelas e migrações
│       ├── medicamento_model.py
│       ├── lote_model.py
│       ├── venda_model.py       ← Vendas, devoluções e resumos
│       ├── pontos_model.py      ← Fidelidade
│       ├── cliente_model.py
│       ├── fornecedor_model.py
│       ├── pedido_model.py      ← Encomendas online
│       ├── notificacao_model.py
│       ├── alerta_model.py      ← Alertas de stock/validade
│       ├── relatorio_model.py
│       ├── usuario_model.py
│       └── log_model.py
├── frontend/
│   ├── login.html · registar.html · index.html
│   ├── dashboard.html
│   ├── medicamentos.html · lotes.html
│   ├── vendas.html · pedidos.html
│   ├── clientes.html · fornecedores.html
│   ├── relatorios.html · historico.html · usuarios.html
│   ├── portal.html · ajuda.html · 404.html
│   ├── css/  ·  img/
│   └── js/
│       ├── config.js            ← URL da API (mudar aqui para produção)
│       ├── app.js               ← Base partilhada (menu, sino, exportação)
│       ├── mapa.js              ← Mapas (Leaflet/OpenStreetMap)
│       ├── talao.js             ← Talão dos pedidos
│       └── (login, medicamentos, vendas, pedidos, clientes, ...).js
├── tests/                       ← 174 testes de pytest (test_*.py)
│                                  + scripts de relatório manuais (testar_*.py)
├── requirements-dev.txt
├── pytest.ini
└── README.md
```

---

## Instalação e execução

**Pré-requisitos:** Python 3.11+ instalado.

**1. Obter o código e entrar na pasta**
```bash
git clone <url-do-repositorio>
cd farmacia_api
```

**2. (Opcional, recomendado) Criar um ambiente virtual**
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
```

**3. Instalar as dependências**
```bash
pip install -r requirements-dev.txt
```

**4. Definir a chave secreta**

Copia `backend/.env.example` para `backend/.env` e define uma chave aleatória:
```
SECRET_KEY="uma-chave-secreta-bem-aleatoria"
```

**5. Arrancar a API** (a partir da pasta que contém `backend/`)
```bash
python -m uvicorn backend.main:app --reload
```
A API fica em `http://127.0.0.1:8000`. A documentação interativa (Swagger) está em
`http://127.0.0.1:8000/docs`. A base de dados e o utilizador administrador são
criados automaticamente no primeiro arranque.

**6. Abrir o frontend**

Abre `frontend/login.html` no navegador (ou serve a pasta `frontend/` com um
servidor de ficheiros estáticos). O endereço da API está em `frontend/js/config.js`.

---

## Perfis de utilizador

| Perfil | Acesso |
|---|---|
| **Administrador** | Tudo, incluindo utilizadores, backup/restauro e exportação de vendas |
| **Funcionário** | Operação diária: stock, vendas, devoluções, pedidos, clientes, fornecedores |
| **Cliente** | Portal de encomendas online e as suas próprias encomendas |

**Administrador criado por omissão:**
- Email: `admin@farmacia.cv`
- Palavra-passe: `admin123`

> Altera a palavra-passe do administrador após o primeiro acesso.

---

## Testes

O projeto tem **174 testes automáticos** com `pytest`. Cada teste corre numa base
de dados temporária isolada, cobrindo autenticação, permissões, regras de negócio
e casos-limite (ex.: integridade de stock em devoluções e anulações).

```bash
python -m pytest -q
```

Existem também *scripts* de relatório manuais (`tests/testar_*.py`) que percorrem
um fluxo completo passo a passo com um relatório legível — úteis para demonstração.
O `pytest` **não** os corre (têm o prefixo `testar_`, não `test_`):
```bash
python tests/testar_vendas.py
```

---

## Notas de configuração

- **`SECRET_KEY`** — obrigatória, definida em `backend/.env`. Sem ela a aplicação
  não arranca. Nunca a versionar.
- **Endereço da API** — está centralizado em `frontend/js/config.js` (`API_URL`).
  Para produção, muda apenas essa linha.
- **Base de dados** — `backend/models/farmacia.db` é criada automaticamente e não
  deve ser versionada. As colunas novas são migradas automaticamente no arranque.
- **Mapas** — usam Leaflet + OpenStreetMap (sem chave de API). As páginas precisam
  de ligação à internet para carregar os mapas.