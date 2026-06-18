# 💊 Farmácia CV — Sistema de Gestão

API REST com FastAPI + frontend HTML/Bootstrap para gestão de medicamentos.

## Estrutura do Projeto

```
farmacia_api/
├── backend/
│   ├── main.py                         ← Servidor FastAPI (ponto de entrada)
│   ├── auth/
│   │   └── auth.py                     ← Criação e verificação de JWT
│   ├── controllers/
│   │   ├── dashboard.py
│   │   └── medicamentos.py
│   └── models/
│       ├── db.py                       ← Conexão SQLite e criação de tabelas
│       ├── medicamento_model.py        ← Operações CRUD de medicamentos
│       └── farmacia.db                 ← Base de dados (criada automaticamente)
├── frontend/
│   ├── login.html
│   ├── dashboard.html
│   ├── medicamentos.html
│   ├── style.css
│   └── app.js
├── requirements.txt
└── README.md
```

## Como Correr

### 1. Instalar dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar o servidor
```bash
cd farmacia_api
uvicorn backend.main:app --reload
```

### 3. Abrir o frontend
Abrir `frontend/login.html` no browser.

**Credenciais padrão:**
- Email: `admin@farmacia.cv`
- Senha: `admin123`

## Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/login` | Autenticação |
| GET | `/dashboard` | Resumo geral (protegido) |
| GET | `/medicamentos` | Listar todos (protegido) |
| GET | `/medicamentos/{id}` | Obter um (protegido) |
| POST | `/medicamentos` | Criar novo (protegido) |
| PUT | `/medicamentos/{id}` | Editar (protegido) |
| DELETE | `/medicamentos/{id}` | Apagar (protegido) |

Documentação automática disponível em: `http://127.0.0.1:8000/docs`
