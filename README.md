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
- **Session System**: Sistema completo de gerenciamento de sessões com persistência
- **Chat Memory**: PostgreSQL integrado ao n8n para memória de conversas
- **Automation**: n8n para workflows e orquestração avançada
- **LLMs**: OpenAI GPT-4o-mini e Google Gemini para processamento
- **Containers**: Docker Compose para orquestração completa

## 🚀 Instalação e Configuração

### 📋 Pré-requisitos

- **Windows 10/11** (versão 2004 ou superior)
- **WSL2** instalado e configurado
- **Docker Desktop** com integração WSL2
- **OpenAI API Key** (obrigatório)
- **Git** para clone do repositório

### 🔧 Tutorial Completo: Windows + WSL2 + Docker

#### 1. Instalação do WSL2 no Windows

**Opção A: Instalação Automática (Windows 11/10 versão 2004+)**

```powershell
# Abrir PowerShell como Administrador e executar:
wsl --install
```

**Opção B: Instalação Manual**

```powershell
# 1. Habilitar recursos do Windows
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 2. Reiniciar o computador

# 3. Baixar e instalar o pacote de atualização do kernel WSL2
# Download: https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi

# 4. Definir WSL2 como padrão
wsl --set-default-version 2

# 5. Instalar distribuição Linux (recomendado: Ubuntu 22.04 LTS)
wsl --install -d Ubuntu-22.04
```

#### 2. Configuração Inicial do Ubuntu no WSL2

```bash
# Após a instalação, configurar usuário e senha
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependências essenciais
sudo apt install -y curl wget git unzip
```

#### 3. Instalação e Configuração do Docker Desktop

**3.1. Download e Instalação**

1. Baixar Docker Desktop: https://docs.docker.com/desktop/install/windows-install/
2. Executar o instalador como Administrador
3. **IMPORTANTE**: Marcar "Use WSL 2 instead of Hyper-V" durante instalação

**3.2. Configuração da Integração WSL2**

1. Abrir Docker Desktop
2. Ir em **Settings** → **General**
3. Marcar ✅ "Use the WSL 2 based engine"
4. Ir em **Settings** → **Resources** → **WSL Integration**
5. Marcar ✅ "Enable integration with my default WSL distro"
6. Marcar ✅ sua distribuição Ubuntu
7. Clicar **Apply & Restart**

**3.3. Verificação da Integração**

```bash
# No terminal WSL2 Ubuntu, verificar se Docker está disponível:
docker --version
docker-compose --version

# Testar com container simples:
docker run hello-world
```

#### 4. Otimizações Recomendadas

**4.1. Limitar Uso de Memória do WSL2**

Criar arquivo `.wslconfig` no diretório do usuário Windows:

```ini
# C:\Users\[SeuUsuario]\.wslconfig
[wsl2]
memory=8GB
processors=4
swap=2GB
localhostForwarding=true
```

**4.2. Configurar Git no WSL2**

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
git config --global init.defaultBranch main
```

#### 5. Instalação do Projeto RAG-Demo

**5.1. Clonar o Repositório**

```bash
# No terminal WSL2 Ubuntu:
cd ~
git clone [URL-DO-REPOSITORIO]
cd rag-demo
```

**5.2. Verificar Requisitos**

```bash
# Verificar Docker
docker --version
docker-compose --version

# Verificar se Docker daemon está rodando
docker info
```

### 🚀 Instalação Automática (Recomendado)

```bash
# No terminal WSL2 Ubuntu:
# Execute o script de setup automatizado
chmod +x setup.sh
./setup.sh

# Para primeiro uso (modo desenvolvimento com todos os serviços):
./setup.sh --dev

# Para ambiente de produção:
./setup.sh
```

### ⚠️ Troubleshooting WSL2 + Docker

**Problema: Docker não encontrado no WSL2**
```bash
# Verificar se Docker Desktop está rodando no Windows
# Reiniciar Docker Desktop e verificar integração WSL2
```

**Problema: Permissões de arquivo**
```bash
# No WSL2, garantir que está no diretório home do usuário Linux
cd ~ && pwd  # deve mostrar /home/username
```

**Problema: Portas não acessíveis**
```bash
# Verificar se localhostForwarding está habilitado no .wslconfig
# Reiniciar WSL: wsl --shutdown (no PowerShell Windows)
```

### 2. Configuração Manual

```bash
# 1. Criar arquivo de ambiente
cp env.example .env

# 2. Editar .env com sua OpenAI API Key
nano .env

# 3. Criar diretórios necessários
mkdir -p uploads volumes/{minio,qdrant}

# 4. Iniciar serviços
docker-compose up -d

# 5. Aguardar inicialização (30-60s)
docker-compose logs -f rag-demo-app
```

### 3. Acesso às Aplicações

- 🌐 **RAG-Demo**: http://localhost:5000
- 🔍 **Qdrant Dashboard**: http://localhost:6333/dashboard
- 📦 **MinIO Console**: http://localhost:9001 (`minioadmin` / `minioadmin`)
- 🗄️ **PostgreSQL**: localhost:5432 (`chat_user` / `chat_password`)
- 🔧 **n8n Workflows**: http://localhost:5678 (`admin` / `admin123`)

### 4. 🗄️ Banco de Dados PostgreSQL

O PostgreSQL é utilizado para **dois propósitos principais**:

#### **A. Histórico de Conversas e Sessões**
- **Tabela `chat_sessions`**: Armazena informações das sessões de chat
- **Tabela `session_messages`**: Histórico completo de todas as mensagens
- **Persistência**: Conversas são mantidas entre reinicializações
- **Recuperação**: Sistema de carregamento de sessões antigas

#### **B. Memória do Chat para n8n**
- **Tabela `chat_messages`**: Usada pelo n8n para memória de conversas
- **Integração LangChain**: Compatível com PostgresChatMemory
- **Contexto persistente**: n8n mantém histórico entre execuções
- **Session tracking**: Rastreamento automático de sessões

#### **Configuração do PostgreSQL:**
```bash
# Credenciais padrão
Host: localhost:5432
Database: chat_memory
User: chat_user
Password: chat_password

# Inicialização automática
docker-compose up postgres
```

#### **Estrutura do Banco:**
```sql
-- Sessões de chat
chat_sessions (session_id, name, created_at, last_activity, metadata)

-- Mensagens das sessões
session_messages (id, session_id, role, content, sources, created_at)

-- Memória do n8n
chat_messages (id, session_id, message, metadata, created_at, updated_at)
```

## 📱 Funcionalidades

### 1. 📤 Upload de Documentos

- **Formatos suportados**: PDF, DOCX, TXT, MD (até 10MB)
- **Processamento automático**: LLM melhora formatação e estrutura
- **Vetorização**: Conversão para embeddings usando OpenAI
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
├── 📄 app.py                       # Aplicação Flask principal
├── 📄 docker-compose.yml           # Configuração containers
├── 📄 requirements.txt             # Dependências Python
├── 📄 setup.sh                     # Script de instalação
└── 📄 .env.example                 # Template de configuração
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
# OpenAI (Obrigatório)
OPENAI_API_KEY=sk-your-openai-key-here
MODEL_QA_GENERATOR=gpt-4o-mini

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

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chat_memory
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=chat_password

# Flask
FLASK_ENV=production
FLASK_DEBUG=false

# Embedding
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
```

### Modelos de Embedding Suportados

| Modelo | Provider | Dimensões | Uso Recomendado |
|--------|----------|-----------|-----------------|
| `text-embedding-3-small` | OpenAI | 1536 | Geral, rápido |
| `text-embedding-3-large` | OpenAI | 3072 | Alta precisão |
| `text-embedding-ada-002` | OpenAI | 1536 | Legacy, compatível |

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

# Backup do banco
docker-compose exec postgres pg_dump -U chat_user chat_memory > backup.sql
```

Para mais detalhes, consulte: [docs/postgres-chat-memory.md](docs/postgres-chat-memory.md)

## 🐛 Troubleshooting

### Problemas Comuns

**1. OpenAI API Key inválida**
```bash
# Verificar configuração
docker-compose exec rag-demo-app env | grep OPENAI
```

**2. Qdrant não conecta**
```bash
# Reiniciar serviço
docker-compose restart qdrant

# Verificar logs
docker-compose logs qdrant
```

**3. MinIO sem acesso**
```bash
# Verificar credenciais
echo "minioadmin / minioadmin"

# Acessar console
open http://localhost:9001
```

**4. n8n não carrega**
```bash
# Verificar logs
docker-compose logs n8n

# Reiniciar serviço
docker-compose restart n8n

# Acessar interface
open http://localhost:5678
```

**5. Upload falha**
- Verificar tamanho do arquivo (máx 10MB)
- Confirmar formato suportado (PDF, DOCX, TXT, MD)
- Verificar logs da aplicação

**6. Chat não responde**
- Verificar se há documentos na collection
- Confirmar OpenAI API Key válida
- Verificar logs de erro no console

**7. PostgreSQL não conecta**
```bash
# Verificar se o serviço está rodando
docker-compose ps postgres

# Verificar logs
docker-compose logs postgres

# Testar conexão
python scripts/test-postgres-connection.py

# Reiniciar serviço
docker-compose restart postgres

# Verificar tabelas
docker-compose exec postgres psql -U chat_user -d chat_memory -c "\dt"

# Verificar sessões
docker-compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM chat_sessions;"
```

**8. Histórico de conversas não carrega**
```bash
# Verificar tabela de mensagens
docker-compose exec postgres psql -U chat_user -d chat_memory -c "SELECT COUNT(*) FROM session_messages;"

# Verificar sessões ativas
docker-compose exec postgres psql -U chat_user -d chat_memory -c "SELECT session_id, name, message_count FROM chat_sessions ORDER BY last_activity DESC LIMIT 5;"

# Reinicializar sistema de sessões
./scripts/setup-session-system.sh
```

### Reset Completo

```bash
# Parar todos os serviços
docker-compose down

# Remover volumes (CUIDADO: perde dados)
docker-compose down -v

# Rebuild e restart
docker-compose build --no-cache
docker-compose up -d
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

## 🎯 Versão Beta v3.0

### 🆕 Novidades da Versão Beta

- **✅ Suporte Completo WSL2**: Instalação e configuração otimizada para Windows + WSL2
- **✅ Verificações Automáticas**: Script de setup inteligente com detecção de ambiente
- **✅ Sistema de Analytics**: Estatísticas avançadas de uso das sessões de chat
- **✅ Feedback de Usuários**: Sistema para avaliação da qualidade das respostas
- **✅ Configurações Avançadas**: Preferências de modelo, temperatura e contexto por sessão
- **✅ Interface Aprimorada**: Design responsivo e experiência de usuário melhorada
- **✅ PostgreSQL Otimizado**: Base de dados com funcionalidades beta incluídas

### 🔧 Para Desenvolvedores

```bash
# Modo desenvolvimento (hot-reload ativado)
./setup.sh --dev

# Verificar logs em tempo real
docker-compose logs -f rag-demo-app

# Reset completo do ambiente
./setup.sh --clean --rebuild
```

### 📊 Funcionalidades Beta

#### Sistema de Analytics
- Estatísticas de uso por sessão
- Contagem de tokens consumidos
- Tempo médio de resposta
- Collections mais utilizadas

#### Feedback de Usuários
- Avaliação de respostas (1-5 estrelas)
- Comentários sobre qualidade
- Análise de relevância

#### Configurações Avançadas
- Escolha de modelo de LLM por sessão
- Controle de temperatura (criatividade)
- Ajuste de janela de contexto
- Personalização de parâmetros

### 🐛 Reportar Issues

Como esta é uma versão beta, sua contribuição é valiosa:

1. **Bugs**: Reporte via [GitHub Issues](https://github.com/seu-usuario/rag-demo/issues)
2. **Sugestões**: Use [GitHub Discussions](https://github.com/seu-usuario/rag-demo/discussions)
3. **Documentação**: Contribua com melhorias na documentação

### 📈 Roadmap

- [ ] Suporte a mais provedores de LLM (Anthropic, Google)
- [ ] Sistema de autenticação de usuários
- [ ] Dashboard de analytics em tempo real
- [ ] Integração com mais formatos de documento
- [ ] API REST completa para integrações externas

---

**RAG-Demo v3.0 Beta** - Transformando o aprendizado de PLN com tecnologia de ponta! 🚀

> _"A melhor forma de aprender é praticando com ferramentas reais."_

### 🎓 Versão Educacional

Esta versão beta foi especialmente preparada para:
- **Estudantes de PLN**: Experimentação prática com RAG
- **Pesquisadores**: Plataforma para testes e desenvolvimento
- **Educadores**: Ferramenta de ensino completa e funcional
- **Desenvolvedores**: Base sólida para projetos RAG 