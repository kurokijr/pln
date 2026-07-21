# RAG-Demo - Plataforma Educacional de PLN

Uma aplicação educacional completa desenvolvida para demonstrar o funcionamento integrado de uma arquitetura baseada em **Recuperação Aumentada por Geração (RAG)**, utilizando tecnologias modernas e APIs de LLMs.

## 🎯 Objetivo

O RAG-Demo é uma plataforma voltada para alunos da disciplina de **Processamento de Linguagem Natural (PLN)**, permitindo experimentação prática com:

- 📄 **Upload e processamento** de documentos (PDF, DOCX, TXT, MD)
- 🔍 **Vetorização inteligente** usando modelos de embedding via API
- 🗄️ **Armazenamento vetorial** no Qdrant (vetores e embeddings)
- 🗃️ **Banco de dados PostgreSQL** para histórico de conversas e sessões
- 💬 **Chat RAG** com múltiplas sessões e contexto persistente
- ❓ **Geração automática** de perguntas e respostas
- ✏️ **Editor de conteúdo** com Markdown e preview
- 🎨 **Interface web moderna** e responsiva

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │   Qdrant        │
│   (HTML/JS/CSS) │◄──►│   (Python API)  │◄──►│   (Vectors)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MinIO         │    │   n8n           │    │OpenAI/GEMINI API│
│   (Storage)     │◄──►│   (Workflows)   │◄──►│      (LLMs)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐
│   PostgreSQL    │
│   (Chat Memory) │
└─────────────────┘
```

### 🔧 Componentes Principais

- **Frontend**: Interface responsiva com Tailwind CSS e JavaScript vanilla
- **Backend**: Flask com APIs REST e Socket.IO para tempo real
- **Vector Store**: Qdrant para armazenamento de vetores e embeddings
- **Storage**: MinIO para armazenamento de arquivos e documentos
- **Database**: PostgreSQL para histórico de conversas e sessões de chat
- **pgAdmin**: Interface web para administração do PostgreSQL
- **Session System**: Sistema completo de gerenciamento de sessões com persistência
- **Chat Memory**: PostgreSQL integrado ao n8n para memória de conversas
- **Automation**: n8n para workflows e orquestração avançada
- **LLMs**: OpenAI GPT-4o-mini e Google Gemini para processamento
- **Containers**: Docker Compose para orquestração completa

## 🚀 Instalação e Configuração

Guia pensado para alunos **sem experiência prévia com Docker**. Siga os passos na ordem. Se algo falhar, use a seção [Troubleshooting](#troubleshooting) no final deste README.

### Em poucas palavras (caminho feliz)

1. Instale **WSL2 + Ubuntu** e o **Docker Desktop** (com integração WSL).
2. Crie uma **OpenAI API Key**.
3. No terminal Ubuntu (WSL), clone o projeto e rode `./setup.sh`.
4. Abra http://localhost:5000 no navegador.

**O que é Docker?** Docker empacota a aplicação e seus serviços (banco, storage, n8n, etc.) em *containers*, para que todos rodem o mesmo ambiente sem instalar Python, PostgreSQL ou Qdrant na mão. O Docker Desktop cuida disso no Windows; no WSL você só digita os comandos.

> **Nota sobre comandos:** Nestas instruções usamos `docker compose` (plugin moderno). Se o seu ambiente só tiver o comando antigo, troque por `docker-compose` — no Docker Desktop ambos costumam funcionar.

### 📋 Pré-requisitos

| Item | Observação |
|------|------------|
| Windows 10/11 | 10 versão **2004+** (Build **19041+**) ou Windows 11 — [docs](https://learn.microsoft.com/pt-br/windows/wsl/install) |
| WSL 2 + Ubuntu | Instalado nos passos abaixo (`wsl -l -v` → VERSION **2**) |
| Docker Desktop | Com integração WSL2 |
| Conta OpenAI + API Key | Obrigatória para embeddings/chat |
| Git | Instalado no Ubuntu (passo 2) |
| ~8 GB RAM livres | Recomendado para subir todos os serviços |

Alunos em **macOS** ou **Linux nativo**: instale [Docker Desktop](https://docs.docker.com/get-docker/) (ou Docker Engine + Compose), pule os passos de WSL e comece em [Passo 4](#passo-4--obter-a-chave-da-openai).

---

<a id="passo-1-wsl2"></a>

### Passo 1 — Instalar o WSL 2 (Windows)

Documentação oficial (Microsoft Learn):

- [Instalar o WSL](https://learn.microsoft.com/pt-br/windows/wsl/install)
- [Instalação manual (versões antigas)](https://learn.microsoft.com/pt-br/windows/wsl/install-manual)
- [Solução de problemas do WSL](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting)
- [Comandos básicos](https://learn.microsoft.com/pt-br/windows/wsl/basic-commands)
- [Boas práticas de ambiente](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment)

#### 1.1 Pré-requisitos (oficiais)

- **Windows 10** versão **2004** ou superior (**Build 19041+**), ou **Windows 11**
- Em builds mais antigos, use a [instalação manual](https://learn.microsoft.com/pt-br/windows/wsl/install-manual)
- Virtualização habilitada na BIOS/UEFI (Intel VT-x / AMD-V). Guia: [habilitar virtualização](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting#error-0x80370102-the-virtual-machine-could-not-be-started-because-a-required-feature-is-not-installed)
- Distribuições WSL devem ficar no **disco do sistema** (normalmente `C:`)

Confira a versão do Windows (PowerShell ou CMD):

```powershell
winver
# ou
cmd.exe /c ver
```

#### 1.2 Instalação recomendada (comando único)

1. Abra o **PowerShell como Administrador** (botão direito → *Executar como administrador*).
2. Execute:

```powershell
wsl --install
```

Segundo a Microsoft, esse comando:

- habilita os componentes necessários do WSL;
- baixa/instala o kernel Linux mais recente;
- define **WSL 2** como padrão;
- instala a distribuição **Ubuntu** (padrão).

3. **Reinicie o computador** quando solicitado.
4. Na primeira abertura do Ubuntu, aguarde a descompactação e crie **usuário** e **senha** do Linux.

> **Nota oficial:** `wsl --install` só instala o WSL “do zero”. Se o WSL **já existir** e o comando mostrar a **ajuda**, use os passos abaixo para instalar/atualizar a distro.

#### 1.3 WSL já instalado — adicionar Ubuntu / corrigir instalação travada

```powershell
# Listar distros disponíveis online
wsl --list --online

# Instalar Ubuntu (ajuste o nome conforme a lista)
wsl --install -d Ubuntu

# Se a instalação travar em 0,0% (correção oficial):
wsl --install --web-download -d Ubuntu
```

Atualizar o WSL / kernel (recomendado pela Microsoft em instalações modernas):

```powershell
wsl --update
wsl --version
```

#### 1.4 Verificar se está em WSL 2 (obrigatório para Docker Desktop)

```powershell
wsl --list --verbose
# atalho equivalente: wsl -l -v
```

A coluna **VERSION** da sua distro (ex.: Ubuntu) deve ser **2**.

Se estiver em **1**, converta (exemplo oficial):

```powershell
wsl --set-default-version 2
wsl --set-version Ubuntu 2
```

Substitua `Ubuntu` pelo nome exato mostrado em `wsl -l -v` (pode ser `Ubuntu-22.04`, `Ubuntu-24.04`, etc.).

#### 1.5 Instalação manual (só se `wsl --install` não estiver disponível)

Siga o guia oficial passo a passo: [Instalação manual do WSL](https://learn.microsoft.com/pt-br/windows/wsl/install-manual).

Resumo alinhado à documentação:

```powershell
# 1) Habilitar componentes (PowerShell Admin) — reinicie depois
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

```powershell
# 2) Após reiniciar: atualizar kernel / WSL
# Pacote de kernel (legado / docs): https://aka.ms/wsl2kernel
# Ou, se o comando existir:
wsl --update

# 3) Definir WSL 2 como padrão e instalar Ubuntu
wsl --set-default-version 2
wsl --install -d Ubuntu
```

Em ambientes **offline**, a Microsoft recomenda o MSI em [WSL Releases (GitHub)](https://github.com/microsoft/WSL/releases) + componente `VirtualMachinePlatform` — detalhes em [Instalar o WSL → Instalação offline](https://learn.microsoft.com/pt-br/windows/wsl/install#offline-install).

#### 1.6 Correções oficiais comuns na instalação

Se falhar, consulte a seção *Installation issues* em [Solução de problemas do WSL](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting#installation-issues). Resumo:

| Sintoma / código | Correção oficial (resumo) |
|------------------|---------------------------|
| `0x80370102` / VM não inicia | Habilitar **Virtual Machine Platform** e **virtualização na BIOS**; Hypervisor: `bcdedit /set hypervisorlaunchtype Auto` |
| `WSL 2 requires an update to its kernel` / `0x1bc` | Atualizar kernel: `wsl --update` ou [aka.ms/wsl2kernel](https://aka.ms/wsl2kernel) |
| `0x8007019e` / WSL não habilitado | Habilitar o recurso WSL e **reiniciar** |
| Instalação em **0,0%** | `wsl --install --web-download -d Ubuntu` |
| Distro no disco errado | Salvar apps/conteúdo novo no disco `C:` (Configurações → Sistema → Armazenamento) |
| VHD comprimido/criptografado | Em `%LocalAppData%\Packages\...LocalState`, desmarque compactar/criptografar |
| Hypervisors de terceiros | VMware/VirtualBox atualizados (com suporte a Hyper-V) ou desligados |

Depois de corrigir, sempre valide com `wsl -l -v` (VERSION = **2**).

---

### Passo 2 — Preparar o Ubuntu no WSL 2

Abra o **Ubuntu** (menu Iniciar) ou, no PowerShell: `wsl`.

Na primeira execução, crie usuário/senha do Linux. Em seguida:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git unzip
```

Dicas oficiais úteis neste projeto:

- Prefira trabalhar em `/home/<usuario>/...` (filesystem Linux), não em `/mnt/c/...` — ver [boas práticas](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment).
- Terminal recomendado: [Windows Terminal](https://learn.microsoft.com/pt-br/windows/terminal/install).

---

### Passo 3 — Instalar e integrar o Docker Desktop

1. Baixe: https://docs.docker.com/desktop/install/windows-install/
2. Instale **como Administrador**.
3. Durante a instalação, marque **Use WSL 2 instead of Hyper-V** (se aparecer).
4. Abra o Docker Desktop e configure:
   - **Settings → General** → ✅ *Use the WSL 2 based engine*
   - **Settings → Resources → WSL Integration** → ✅ *Enable integration with my default WSL distro* e ✅ Ubuntu
   - **Apply & Restart**
5. No terminal Ubuntu, confira:

```bash
docker --version
docker compose version
docker info
docker run hello-world
```

Se `docker` não for encontrado ou `docker info` falhar, veja [Docker / WSL](#1-docker--wsl2) no Troubleshooting.

---

<a id="passo-4--obter-a-chave-da-openai"></a>

### Passo 4 — Obter a chave da OpenAI

1. Acesse https://platform.openai.com/api-keys (crie conta se necessário).
2. Crie uma API key e copie (começa com `sk-`).
3. Guarde em local seguro — ela será pedida no próximo passo (arquivo `.env`).

---

### Passo 5 — Clonar o projeto e instalar (recomendado)

No terminal **Ubuntu (WSL)**:

```bash
cd ~
git clone https://github.com/kurokijr/pln.git
cd pln
chmod +x setup.sh
./setup.sh
```

O script:

- cria `.env` a partir de `env.example` (se ainda não existir);
- pede para você colar a `OPENAI_API_KEY`;
- sobe todos os serviços (app, Qdrant, MinIO, PostgreSQL, pgAdmin, n8n).

#### Sobre `./setup.sh --dev`

Para **usar as funcionalidades** da plataforma (upload, chat, collections, n8n, etc.), **não use `--dev`**. O comando padrão `./setup.sh` basta.

Use `--dev` **somente se for mexer no código-fonte** (`src/`, `templates/`, `static/`). Nesse modo o script:

- ativa Flask em debug;
- monta o código do host no container (hot-reload, sem rebuild a cada alteração);
- sobe o stack de desenvolvimento (sem o pgAdmin na lista explícita do script).

**Qual comando usar?**

| Situação | Comando |
|----------|---------|
| Aula / uso das funcionalidades (recomendado) | `./setup.sh` |
| Editar código-fonte (hot-reload + debug) | `./setup.sh --dev` |
| Limpar dados com cuidado | `./setup.sh --clean` |
| Rebuild completo | `./setup.sh --clean --rebuild` |

Aguarde 1–3 minutos na primeira execução (download de imagens).

---

### Passo 6 — Acessar as aplicações

| Serviço | URL / host | Login padrão (lab local) |
|---------|------------|---------------------------|
| **RAG-Demo** | http://localhost:5000 | — |
| Qdrant | http://localhost:6333/dashboard | — |
| MinIO | http://localhost:9001 | `minioadmin` / `minioadmin` |
| PostgreSQL | `localhost:5432` | `chat_user` / `chat_password` |
| pgAdmin | http://localhost:5050 | `admin@example.com` / `admin` |
| n8n | http://localhost:5678 | `admin` / `admin123` |

Credenciais padrão são só para ambiente educacional local.

Comandos úteis no dia a dia:

```bash
docker compose ps              # status
docker compose logs -f         # logs de todos
docker compose logs -f rag-demo-app
docker compose down            # parar
docker compose up -d           # subir de novo
```

---

### Alternativa — Configuração manual (sem `setup.sh`)

Use se o script automático falhar e você quiser subir o stack na mão:

```bash
cd ~/pln
cp env.example .env
nano .env   # preencha OPENAI_API_KEY=sk-...
mkdir -p uploads volumes/{minio,qdrant,postgres,n8n}
docker compose up -d
docker compose logs -f rag-demo-app
```

---

### Opcional — Ajustes do WSL (`.wslconfig`)

Só se o PC travar ou o Docker ficar lento. Documentação oficial: [Configuração do WSL (`.wslconfig`)](https://learn.microsoft.com/pt-br/windows/wsl/wsl-config).

Crie `C:\Users\<SeuUsuario>\.wslconfig` (no Windows):

```ini
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

No PowerShell: `wsl --shutdown`, depois abra o Ubuntu de novo.

Git (opcional):

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

---

### Banco de Dados PostgreSQL e pgAdmin

O PostgreSQL guarda:

- **Sessões e histórico** (`chat_sessions`, `session_messages`);
- **Memória do chat no n8n** (`chat_messages`).

Credenciais padrão: host `localhost:5432`, database `chat_memory`, user `chat_user`, password `chat_password`.

```bash
docker compose up -d postgres pgadmin
```

No pgAdmin (http://localhost:5050), use o host **`postgres`** (rede Docker), não `localhost`. Servidor pré-cadastrado: *PostgreSQL (chat_memory)*. Detalhes: [docs/pgadmin.md](docs/pgadmin.md).

## 📱 Funcionalidades

### 1. 📤 Upload de Documentos

- **Formatos suportados**: PDF, DOCX, TXT, MD (até 10MB)
- **Processamento automático**: LLM melhora formatação e estrutura
- **Vetorização**: Conversão para embeddings via OpenAI ou Google Gemini
- **Armazenamento**: Documentos no MinIO, vetores no Qdrant

### 2. 🗂️ Gerenciamento de Collections

### 3. 💬 Sistema de Sessões de Chat

- **Sessões únicas**: Cada conversa tem um sessionID único
- **Persistência completa**: Histórico salvo no PostgreSQL
- **Recuperação de conversas**: Clique no sessionID para carregar histórico
- **Integração com N8N**: sessionID sempre enviado ao multiagente
- **Interface intuitiva**: Gerenciamento de sessões no frontend

#### Como usar o sistema de sessões:

1. **Acesse a aba "Histórico"**
2. **Clique em "Nova Sessão"** para criar uma conversa
3. **Vá para "Chat Multi-Agente"** e digite sua pergunta
4. **O sessionID será enviado automaticamente** ao N8N
5. **Volte ao histórico** para ver todas as sessões salvas
6. **Clique em uma sessão** para carregar a conversa completa

#### Setup do sistema de sessões:

```bash
# Inicializar banco de dados de sessões
./scripts/setup-session-system.sh

# Testar o sistema
python scripts/test_session_system.py
```

### 4. 💬 Chat Multi-Agente

- **Criação inteligente**: Collections baseadas em modelo de embedding
- **Múltiplos modelos**: Suporte a diferentes dimensões de vetores
- **Validação**: Prevenção de mistura de embeddings incompatíveis
- **Interface visual**: Listagem, filtros e estatísticas em tempo real

### 3. ✏️ Editor de Conteúdo Q&A

- **Geração automática**: Criação de perguntas e respostas baseada em documentos
- **Configurações avançadas**:
  - Número de Q&As (1-500)
  - Nível de dificuldade (Iniciante, Intermediário, Avançado)
  - Criatividade (temperature 0.0-1.0)
  - Palavras-chave para foco
- **Preview dinâmico**: Visualização formatada e edição Markdown
- **Vetorização opcional**: Inserção das Q&As como embeddings

### 4. 💬 Chat RAG Inteligente

- **Múltiplas sessões**: Conversas independentes com histórico
- **Busca semântica**: Recuperação de contexto relevante
- **Respostas contextualizadas**: Baseadas em documentos específicos
- **Interface moderna**: Design conversacional com typing indicators

### 5. 📊 Métricas e Analytics

- **Estatísticas de documentos**: Caracteres, palavras, complexidade
- **Contagem real**: Documentos e embeddings por collection
- **Progress tracking**: Status de processamento em tempo real

### 6. 🔧 Workflows Automatizados (n8n)

- **Automação de processamento**: Pipelines personalizáveis para documentos
- **Integração com APIs**: Conectores para serviços externos
- **Webhooks**: Endpoints para triggers automáticos
- **Agendamento**: Execução automática de tarefas

## 🔌 APIs Disponíveis

### Collections
```http
GET    /api/collections              # Listar collections
POST   /api/collections              # Criar collection
DELETE /api/collections/{name}       # Deletar collection
```

### Documentos
```http
POST   /api/upload                   # Upload e vetorização
GET    /api/documents                # Listar documentos
GET    /api/documents/{id}           # Obter documento específico
```

### Q&A Generation
```http
POST   /api/qa-generate              # Gerar perguntas e respostas
POST   /api/vectorize-qa             # Vetorizar Q&As geradas
POST   /api/create-qa-embeddings     # Criar embeddings de Q&A
```

### Chat
```http
POST   /api/chat                     # Processar mensagem
GET    /api/sessions                 # Listar sessões
POST   /api/sessions                 # Criar sessão
DELETE /api/sessions/{id}            # Deletar sessão
```

### Configuração
```http
GET    /api/embedding-models         # Modelos disponíveis
GET    /api/storage-info             # Informações de armazenamento
GET    /api/test                     # Health check
```

### Workflows (n8n)
```http
POST   http://localhost:5678/webhook # Webhooks personalizados
GET    http://localhost:5678/api     # API n8n
```

## 📁 Estrutura do Projeto

```
📦 RAG-Demo/
├── 📁 src/                         # Código fonte Python
│   ├── 📄 config.py               # Configurações e constantes
│   ├── 📄 vector_store.py         # Interface Qdrant + embeddings
│   ├── 📄 document_processor.py   # Processamento de documentos
│   ├── 📄 qa_generator.py         # Geração de Q&A com LLM
│   ├── 📄 storage.py              # Gerenciamento MinIO
│   ├── 📄 chat_rag_service.py     # Serviço de chat RAG
│   ├── 📄 semantic_search_service.py # Serviço de busca semântica
│   └── 📄 similarity_search_service.py # Serviço de busca por similaridade
├── 📁 templates/                   # Templates HTML
│   └── 📄 index.html              # Interface principal (SPA)
├── 📁 static/                      # Assets estáticos
│   ├── 📁 css/                    # Estilos CSS
│   ├── 📁 js/                     # JavaScript
│   └── 📁 images/                 # Imagens e ícones
├── 📁 volumes/                     # Dados persistentes
│   ├── 📁 minio/                  # Arquivos no MinIO
│   ├── 📁 postgres/               # Dados do PostgreSQL
│   ├── 📁 qdrant/                 # Vetores no Qdrant
│   └── 📁 n8n/                    # Workflows n8n
├── 📁 config/                      # Configurações auxiliares
│   └── 📁 pgadmin/                # servers.json do pgAdmin
├── 📁 docs/                        # Documentação do sistema
├── 📄 app.py                       # Aplicação Flask principal
├── 📄 docker-compose.yml           # Configuração containers
├── 📄 requirements.txt             # Dependências Python
├── 📄 setup.sh                     # Script de instalação
└── 📄 env.example                  # Template de configuração
```

## 🔄 Fluxos de Dados

### 1. 📄 Upload e Processamento
```
Arquivo → Upload → LLM Processing → Chunking → Embedding → Qdrant
```

### 2. 💬 Chat RAG
```
Pergunta → Embedding → Busca Qdrant → Contexto → LLM → Resposta → PostgreSQL (Histórico)
```

### 3. ❓ Geração Q&A
```
Documento → Chunking → LLM Generate → Q&A Pairs → Vetorização → Qdrant
```

### 4. 🔍 Busca Semântica
```
Query → Embedding → Similarity Search → Ranking → Results
```

### 5. 💾 Persistência de Sessões
```
Chat → PostgreSQL (session_messages) → Recuperação → Interface
```

## ⚙️ Configuração Avançada

### Variáveis de Ambiente (`.env`)

```env
# OpenAI (obrigatório para o fluxo padrão / setup)
OPENAI_API_KEY=sk-your-openai-key-here
MODEL_QA_GENERATOR=gpt-4o-mini

# Google Gemini (opcional; necessário para embedding/chat com provider gemini)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123
N8N_USERNAME=admin
N8N_PASSWORD=admin123
N8N_REQUEST_TIMEOUT=120  # tempo máximo (s) para aguardar resposta do n8n

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chat_memory
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=chat_password

# pgAdmin
PGADMIN_PORT=5050
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin

# Flask
FLASK_ENV=production
FLASK_DEBUG=false

# Embedding: openai | gemini  (chaves de config.EMBEDDING_MODELS)
DEFAULT_EMBEDDING_MODEL=openai
```

### Modelos de Embedding Suportados

As chaves abaixo são as usadas na API/UI (`/api/embedding-models` e ao criar collections). Definição em `src/config.py`.

| Chave | Modelo da API | Provider | Dimensões | Uso recomendado |
|-------|---------------|----------|-----------|-----------------|
| `openai` | `text-embedding-3-small` | OpenAI | 1536 | Padrão; rápido e econômico |
| `gemini` | `models/gemini-embedding-001` | Google Gemini | 3072 | Alternativa Google; exige `GEMINI_API_KEY` |

Observações:

- Não misture providers na mesma collection (dimensões e espaços vetoriais incompatíveis).
- Padrão: `DEFAULT_EMBEDDING_MODEL=openai` em `.env`.
- Para usar Gemini: preencha `GEMINI_API_KEY` e selecione `gemini` na criação da collection (ou defina `DEFAULT_EMBEDDING_MODEL=gemini`).

## 🛠️ Desenvolvimento

### Execução Local (sem Docker)

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar ambiente
cp env.example .env
# Editar .env conforme necessário

# 3. Iniciar apenas serviços externos
docker-compose up -d qdrant minio

# 4. Executar aplicação
python app.py
```

### Logs e Debug

```bash
# Logs de todos os serviços
docker-compose logs -f

# Logs específicos
docker-compose logs -f rag-demo-app
docker-compose logs -f qdrant

# Debug da aplicação
docker-compose exec rag-demo-app bash
```

### Testes

```bash
# Health check
curl http://localhost:5000/api/test

# Verificar collections
curl http://localhost:5000/api/collections

# Status Qdrant
curl http://localhost:6333/health
```

## 🗄️ PostgreSQL - Memória do Chat

O PostgreSQL foi configurado como serviço de memória do chat para o n8n, seguindo a [documentação oficial](https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.memorypostgreschat/).

### Configuração Rápida

```bash
# Setup automatizado do PostgreSQL
./scripts/setup-postgres.sh

# Ou manualmente
docker-compose up -d postgres
```

### Estrutura do Banco

- **Database**: `chat_memory`
- **Tabela principal**: `chat_messages`
- **Usuário**: `chat_user`
- **Senha**: `chat_password`

### Como Usar no n8n

1. **Configurar credenciais** no n8n (Settings > Credentials > Postgres)
2. **Adicionar Postgres Chat Memory node** ao workflow
3. **Configurar parâmetros**:
   - Session Key: Identificador único da sessão
   - Table Name: `chat_messages`
   - Context Window Length: Número de mensagens para contexto

### Testes e Manutenção

```bash
# Testar conexão
python scripts/test-postgres-connection.py

# Conectar via CLI
docker-compose exec postgres psql -U chat_user -d chat_memory

# Interface web (pgAdmin)
docker compose up -d pgadmin
# http://localhost:5050 — admin@example.com / admin

# Backup do banco
docker-compose exec postgres pg_dump -U chat_user chat_memory > backup.sql
```

Para mais detalhes, consulte: [docs/postgres-chat-memory.md](docs/postgres-chat-memory.md) e [docs/pgadmin.md](docs/pgadmin.md)

## 🗄️ Estrutura Completa de Banco de Dados

### 📊 Visão Geral da Arquitetura de Dados

O RAG-Demo utiliza uma arquitetura de múltiplos bancos especializados para máxima eficiência:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │    │     MinIO       │
│                 │    │                 │    │                 │
│ • Chat Memory   │    │ • Vector DB     │    │ • File Storage  │
│ • Sessions      │    │ • Embeddings    │    │ • Documents     │
│ • Histórico     │    │ • Similarity    │    │ • Uploads       │
│                 │    │ • Search        │    │ • Assets        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🏗️ Schema PostgreSQL Detalhado

#### **Tabelas Principais:**

**1. `chat_messages` - Histórico de Conversas (n8n compatibility)**
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,              -- Conteúdo principal (usado pelo n8n)
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**2. `chat_sessions` - Sessões de chat**
```sql
CREATE TABLE chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    session_name VARCHAR(500),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**3. `session_messages` - Mensagens das sessões (app)**
```sql
CREATE TABLE session_messages (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) REFERENCES chat_sessions(session_id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 🔧 Gerenciamento de Banco de Dados

#### **Criação/Recriação da Estrutura**

**Método 1: Automático (Recomendado)**
```bash
# Setup completo - cria tudo automaticamente
./setup.sh

# Ou com limpeza completa
./setup.sh --clean
```

**Método 2: Manual**
```bash
# Conectar ao PostgreSQL
docker-compose exec postgres psql -U chat_user -d chat_memory

# Executar script de inicialização
\i /docker-entrypoint-initdb.d/init-postgres.sql
```

**Método 3: Reinicialização Completa**
```bash
# Parar serviços
docker-compose down

# Remover volumes (CUIDADO: apaga dados!)
docker volume rm $(docker volume ls -q | grep pln)

# Reiniciar
./setup.sh
```

#### **Testes de Conectividade**

**Teste Automatizado:**
```bash
python scripts/test-postgres-connection.py
```

**Teste Manual:**
```bash
# Conectar ao banco
docker-compose exec postgres psql -U chat_user -d chat_memory

# Verificar tabelas
\dt

# Ver estrutura de uma tabela
\d chat_messages

# Verificar dados
SELECT COUNT(*) FROM chat_messages;
SELECT COUNT(*) FROM chat_sessions;
```

### 🔧 Correção de Permissões dos Volumes

Se `volumes/n8n`, `volumes/postgres`, etc. não forem populados, use a seção [Volumes e permissões](#5-volumes-e-permissões) no Troubleshooting (script `fix-volume-permissions.sh` e correção manual com `chown`).

### 📊 Comandos de Manutenção

#### **Backup e Restauração**
```bash
# Backup completo
docker-compose exec postgres pg_dump -U chat_user chat_memory > backup.sql

# Backup apenas estrutura
docker-compose exec postgres pg_dump -U chat_user -s chat_memory > schema.sql

# Restaurar backup
docker-compose exec -T postgres psql -U chat_user chat_memory < backup.sql
```

#### **Limpeza de Dados**
```bash
# Limpar mensagens antigas (30 dias)
docker-compose exec postgres psql -U chat_user -d chat_memory -c "SELECT cleanup_old_sessions(30);"

# Limpar todas as mensagens (CUIDADO!)
docker-compose exec postgres psql -U chat_user -d chat_memory -c "TRUNCATE chat_messages CASCADE;"
```

### 🔒 Segurança e Permissões

#### **Configuração de Usuários**
```sql
-- Verificar permissões atuais
\dp chat_messages

-- Usuário dedicado para aplicação
GRANT ALL PRIVILEGES ON TABLE chat_messages TO chat_user;
GRANT ALL PRIVILEGES ON TABLE chat_sessions TO chat_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO chat_user;
```

#### **Boas Práticas de Segurança**
- ✅ **Usuário dedicado** (`chat_user`) - nunca usar superuser
- ✅ **Conexões limitadas** - apenas da aplicação
- ✅ **Backup regular** - dados críticos protegidos
- ✅ **Logs auditoria** - rastreamento de atividades
- ✅ **Senhas seguras** - configuradas via variáveis de ambiente

### 🚀 Funcionalidades Avançadas

#### **Triggers Automáticos**
```sql
-- Atualizar timestamp automaticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Aplicar trigger
CREATE TRIGGER update_chat_messages_updated_at
    BEFORE UPDATE ON chat_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

#### **Funções de Limpeza**
```sql
-- Função para limpar dados antigos
CREATE OR REPLACE FUNCTION cleanup_old_sessions(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM chat_messages 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM chat_sessions 
    WHERE last_activity < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
```

### 🔄 Integração com n8n

#### **Configuração no n8n:**
1. **Ir para Settings → Credentials**
2. **Criar nova credencial PostgreSQL:**
   - Host: `postgres`
   - Port: `5432`
   - Database: `chat_memory`
   - User: `chat_user`
   - Password: `chat_password`

3. **Usar PostgreSQL Chat Memory node:**
   - Table Name: `chat_messages`
   - Session Key: `{{ $json.session_id }}`
   - Context Window Length: `10`

#### **Exemplo de Workflow n8n:**
```json
{
  "nodes": [
    {
      "name": "Chat Memory",
      "type": "@n8n/n8n-nodes-langchain.memoryPostgresChat",
      "parameters": {
        "tableName": "chat_messages",
        "sessionKey": "={{ $json.session_id }}",
        "contextWindowLength": 10
      }
    }
  ]
}
```

### 📱 Integração com Frontend

#### **APIs de Sessão:**
```javascript
// Criar nova sessão
const response = await fetch('/api/sessions', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ name: 'Nova Sessão' })
});

// Listar sessões
const sessions = await fetch('/api/sessions').then(r => r.json());

// Carregar mensagens de uma sessão
const messages = await fetch(`/api/sessions/${sessionId}`).then(r => r.json());
```

## 🐛 Troubleshooting

<a id="troubleshooting"></a>

Erros conhecidos e correções. Comece pelo sintoma que você está vendo. Na dúvida, rode `docker compose ps` e `docker compose logs -f` na pasta do projeto (`~/pln`).

<a id="1-docker--wsl2"></a>

### 1. Docker / WSL 2

Documentação oficial WSL: [Solução de problemas](https://learn.microsoft.com/pt-br/windows/wsl/troubleshooting) · [Instalar](https://learn.microsoft.com/pt-br/windows/wsl/install)

**Instalação do WSL falhou / distro não abre**

Siga a tabela de [correções oficiais no Passo 1.6](#passo-1-wsl2) e, se necessário, a seção *Installation issues* do guia Microsoft.

Comandos úteis de diagnóstico (PowerShell):

```powershell
wsl --status
wsl --version
wsl -l -v
wsl --update
```

**Distro em WSL 1 (Docker Desktop exige WSL 2)**

```powershell
wsl --set-version Ubuntu 2
# nome exato: veja em wsl -l -v
```

**Erro `0x80370102` (virtualização / VM Platform)**

1. Habilite **Virtual Machine Platform** (Recursos do Windows) e reinicie.
2. Habilite virtualização na BIOS/UEFI.
3. Confira o hypervisor:

```powershell
bcdedit /enum | findstr -i hypervisorlaunchtype
# se estiver Off:
bcdedit /set hypervisorlaunchtype Auto
```

**Kernel desatualizado** (`WSL 2 requires an update to its kernel component`)

```powershell
wsl --update
# ou pacote oficial: https://aka.ms/wsl2kernel
```

**Docker não encontrado no WSL** (`command not found: docker`)

1. Confirme que o **Docker Desktop está aberto** no Windows.
2. **Settings → Resources → WSL Integration** → Ubuntu marcado → Apply & Restart.
3. Feche e reabra o terminal Ubuntu; teste `docker --version`.

**Docker instalado, mas daemon não responde** (`Cannot connect to the Docker daemon` / `docker info` falha)

1. Abra/reinicie o Docker Desktop.
2. Aguarde o status “Engine running”.
3. No PowerShell: `wsl --shutdown`, abra o Ubuntu e teste de novo.

**`docker compose` não funciona, mas `docker` sim**

```bash
docker compose version
# se falhar, tente o alias legado:
docker-compose version
```

**Portas / localhost não acessíveis no Windows**

1. Em `C:\Users\<SeuUsuario>\.wslconfig`, garanta `localhostForwarding=true` ([docs](https://learn.microsoft.com/pt-br/windows/wsl/wsl-config)).
2. No PowerShell: `wsl --shutdown`.
3. Reabra o Ubuntu e o Docker Desktop; teste http://localhost:5000.

**Permissões / projeto no disco errado**

Prefira clonar em `/home/<usuario>/...` (WSL), não em `/mnt/c/...` — evita lentidão e erros de permissão ([boas práticas](https://learn.microsoft.com/pt-br/windows/wsl/setup/environment)):

```bash
cd ~ && pwd   # deve ser /home/<seu-usuario>
```

**WSL lento ou PC sem memória**

Ajuste `memory` no `.wslconfig` (ex.: `4GB` ou `6GB`) se o Windows ficar sem RAM; ou aumente se os containers forem mortos por OOM. Depois: `wsl --shutdown`.

---

### 2. Setup, `.env` e OpenAI

**`OPENAI_API_KEY` não configurada / inválida**

```bash
# Conferir se a variável chegou no container
docker compose exec rag-demo-app env | grep OPENAI

# Corrigir no host
nano .env   # OPENAI_API_KEY=sk-sua-chave
docker compose up -d --force-recreate rag-demo-app
```

A chave deve começar com `sk-`. Sem créditos/quota na conta OpenAI, o chat e o embedding também falham.

**`setup.sh` aborta pedindo Docker Compose**

Instale/atualize o Docker Desktop e habilite a integração WSL. O script verifica o comando `docker-compose` (symlink do plugin).

**Arquivo de ambiente**

O template correto é `env.example` (não `.env.example`):

```bash
cp env.example .env
```

---

### 3. Serviços (containers)

**Qdrant não conecta / unhealthy**

```bash
docker compose restart qdrant
docker compose logs qdrant
docker compose ps qdrant
```

**MinIO sem acesso**

- Console: http://localhost:9001  
- Login padrão: `minioadmin` / `minioadmin`  
- Se a porta 9001 estiver ocupada, pare o outro processo ou altere a porta no `docker-compose.yml` / `.env`.

**n8n não carrega**

```bash
docker compose logs n8n
docker compose restart n8n
```

Acesse http://localhost:5678 (`admin` / `admin123`). Se credenciais/workflows “sumirem” após rebuild, verifique o volume e o arquivo `volumes/n8n/config` (encryption key) — o script `scripts/ensure-n8n-encryption-key.sh` ajuda a manter a chave estável.

**PostgreSQL não conecta**

```bash
docker compose ps postgres
docker compose logs postgres
docker compose restart postgres
docker compose exec postgres psql -U chat_user -d chat_memory -c "\dt"
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM chat_sessions;"
```

Teste opcional: `python scripts/test-postgres-connection.py` (com dependências locais).

**pgAdmin não abre ou não conecta ao banco**

- URL: http://localhost:5050 (`admin@example.com` / `admin`)
- Host do servidor Postgres **dentro** do Docker: `postgres` (não `localhost`)
- Senha do banco: valor de `POSTGRES_PASSWORD` no `.env` (padrão `chat_password`)
- Detalhes: [docs/pgadmin.md](docs/pgadmin.md)

**Container `unhealthy` ou `exited`**

```bash
docker compose ps
docker compose logs [nome-do-serviço]
docker compose up -d
```

---

### 4. Aplicação (RAG-Demo)

**Upload falha**

- Tamanho máximo: **10 MB**
- Formatos: PDF, DOCX, TXT, MD
- Veja logs: `docker compose logs -f rag-demo-app`

**Chat não responde**

- Confirme `OPENAI_API_KEY` válida e com crédito
- Verifique se há documentos/collection no Qdrant
- Logs: `docker compose logs -f rag-demo-app` e, se usar multiagente, `docker compose logs -f n8n`

**Histórico de conversas não carrega**

```bash
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM session_messages;"
docker compose exec postgres psql -U chat_user -d chat_memory -c "SELECT session_id, name, message_count FROM chat_sessions ORDER BY last_activity DESC LIMIT 5;"
./scripts/setup-session-system.sh
```

---

<a id="5-volumes-e-permissões"></a>

### 5. Volumes e permissões

**Volumes do n8n / PostgreSQL / Qdrant / MinIO não populam em `volumes/`**

Correção automática:

```bash
./scripts/fix-volume-permissions.sh
```

Correção manual:

```bash
docker compose down
sudo chown -R 1000:1000 volumes/n8n/
sudo chown -R 70:70 volumes/postgres/
sudo chown -R 1000:1000 volumes/qdrant/
sudo chown -R 1000:1000 volumes/minio/
docker compose up -d
```

Verificação:

```bash
ls -la volumes/n8n/
sudo ls -la volumes/postgres/
ls -la volumes/qdrant/
ls -la volumes/minio/
```

---

### 6. Reset completo

**Cuidado:** apaga dados dos volumes Docker nomeados.

```bash
docker compose down
# remove volumes (perde dados persistidos nos volumes nomeados)
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

Ou via script:

```bash
./setup.sh --clean --rebuild
```

## 🤝 Contribuição

1. **Fork** o projeto
2. **Crie** uma branch (`git checkout -b feature/nova-funcionalidade`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. **Push** para a branch (`git push origin feature/nova-funcionalidade`)
5. **Abra** um Pull Request

### Convenções

- **Commits**: Use conventional commits (`feat:`, `fix:`, `docs:`)
- **Código**: Siga PEP 8 para Python, Prettier para JavaScript
- **Documentação**: Atualize README.md e docstrings
- **Testes**: Inclua testes para novas funcionalidades

## 📄 Licença

Este projeto está sob a **MIT License** - veja [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- **[Qdrant](https://qdrant.tech/)** - Vector Database de alta performance
- **[MinIO](https://min.io/)** - Object Storage compatível com S3
- **[PostgreSQL](https://www.postgresql.org/)** - Sistema de banco de dados relacional
- **[OpenAI](https://openai.com/)** - APIs de Language Models
- **[LangChain](https://langchain.com/)** - Framework para aplicações LLM
- **[Flask](https://flask.palletsprojects.com/)** - Web framework Python
- **[Tailwind CSS](https://tailwindcss.com/)** - Framework CSS utilitário
- **[n8n](https://n8n.io/)** - Plataforma de automação de workflows

## 📞 Suporte

### Documentação
- 📖 **Wiki**: Documentação completa no repositório
- 🎥 **Tutoriais**: Vídeos explicativos das funcionalidades
- 💡 **Exemplos**: Casos de uso práticos

### Comunidade
- 🐛 **Issues**: Reporte bugs e sugestões
- 💬 **Discussions**: Tire dúvidas e compartilhe conhecimento
- 📧 **Email**: Contato direto com desenvolvedores

## 🎯 Versão Beta v3.2.7

**Data da alteração:** 2026-07-21

### 🆕 Novidades da Versão

- **✅ WSL 2**: instalação alinhada à documentação oficial Microsoft (pt-BR) + correções oficiais
- **✅ Embeddings documentados**: chaves reais `openai` e `gemini` (inclui Google Gemini)
- **✅ Guia de instalação para alunos**: caminho passo a passo (WSL2 → Docker → API key → `./setup.sh`)
- **✅ Clarificação de `--dev`**: só para quem edita código-fonte; uso de funcionalidades usa `./setup.sh`
- **✅ Troubleshooting unificado**: erros conhecidos (Docker/WSL, API, serviços, app, volumes, reset) em uma seção do README
- **✅ pgAdmin**: Interface web Docker para administrar o PostgreSQL (http://localhost:5050) — imagem `dpage/pgadmin4:latest`
- **✅ Verificações Automáticas**: Script de setup inteligente com detecção de ambiente
- **✅ Interface Aprimorada**: Design responsivo e experiência de usuário melhorada
- **✅ PostgreSQL**: Histórico de sessões e memória do chat (n8n)

### Melhorias realizadas (3.2.7)

- [x] Passo 1 (WSL 2) reescrito com links e procedimentos oficiais Microsoft Learn
- [x] Troubleshooting WSL expandido (`0x80370102`, kernel, `wsl --update`, `--web-download`)

### Melhorias realizadas (3.2.6)

- [x] Removidas listas de TO-DO e Roadmap do README
- [x] Removidas “funcionalidades beta” (analytics/feedback) não implementadas na aplicação

### Melhorias realizadas (3.2.5)

- [x] README: tabela de embeddings alinhada a `src/config.py` (`openai` + `gemini`)
- [x] Default de Q&A embeddings corrigido para `config.DEFAULT_EMBEDDING_MODEL`
- [x] `env.example`: `GEMINI_MODEL` atualizado para `gemini-1.5-flash`

### Melhorias realizadas (3.2.4)

- [x] README: `./setup.sh` como padrão; `--dev` documentado só para edição de código-fonte

### Melhorias realizadas (3.2.3)

- [x] README reorganizado: instalação mínima para alunos sem Docker
- [x] Troubleshooting consolidado no README (incluindo WSL2/Docker e volumes)
- [x] Correção de referências (`env.example`, URL do clone, `docker compose`)

### Melhorias realizadas (3.2.2)

- [x] Healthcheck do Qdrant corrigido (`/readyz` via bash; imagem sem `curl`)

### Melhorias realizadas (3.2.1)

- [x] Imagem do pgAdmin atualizada para `dpage/pgadmin4:latest`

### Melhorias realizadas (3.2.0)

- [x] Serviço `pgadmin` no `docker-compose.yml`
- [x] Servidor Postgres pré-cadastrado (`config/pgadmin/servers.json`)
- [x] Documentação em `docs/pgadmin.md` e changelog atualizado

### 🔧 Para Desenvolvedores

Use `--dev` apenas ao alterar o código-fonte (hot-reload + Flask debug). Para só rodar/usar a plataforma, `./setup.sh` é suficiente.

```bash
# Modo desenvolvimento (hot-reload + debug)
./setup.sh --dev

# Verificar logs em tempo real
docker compose logs -f rag-demo-app

# Reset completo do ambiente
./setup.sh --clean --rebuild
```

### 🐛 Reportar Issues

Como esta é uma versão beta, sua contribuição é valiosa:

1. **Bugs**: Reporte via [GitHub Issues](https://github.com/seu-usuario/rag-demo/issues)
2. **Sugestões**: Use [GitHub Discussions](https://github.com/seu-usuario/rag-demo/discussions)
3. **Documentação**: Contribua com melhorias na documentação

---

**RAG-Demo v3.2.7** - Transformando o aprendizado de PLN com tecnologia de ponta! 🚀

> _"A melhor forma de aprender é praticando com ferramentas reais."_

### 🎓 Versão Educacional

Esta versão beta foi especialmente preparada para:
- **Estudantes de PLN**: Experimentação prática com RAG
- **Pesquisadores**: Plataforma para testes e desenvolvimento
- **Educadores**: Ferramenta de ensino completa e funcional
- **Desenvolvedores**: Base sólida para projetos RAG 