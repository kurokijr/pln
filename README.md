# RAG-Demo - Plataforma Educacional de PLN

Uma aplicação educacional completa desenvolvida para demonstrar o funcionamento integrado de uma arquitetura baseada em **Recuperação Aumentada por Geração (RAG)**, utilizando tecnologias modernas e APIs de LLMs.

## 🎯 Objetivo

O RAG-Demo é uma plataforma voltada para alunos da disciplina de **Processamento de Linguagem Natural (PLN)**, permitindo experimentação prática com:

- 📄 **Upload e processamento** de documentos (PDF, DOCX, TXT, MD)
- 🔍 **Vetorização inteligente** usando modelos de embedding via API
- 🗄️ **Armazenamento vetorial** no Qdrant (única fonte de dados)
- 💬 **Chat RAG** com múltiplas sessões e contexto
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
│   MinIO         │    │   n8n           │    │   OpenAI API    │
│   (Storage)     │◄──►│   (Workflows)   │◄──►│   (LLMs)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 🔧 Componentes Principais

- **Frontend**: Interface responsiva com Tailwind CSS e JavaScript vanilla
- **Backend**: Flask com APIs REST e Socket.IO para tempo real
- **Vector Store**: Qdrant como única fonte de dados (sem SQL)
- **Storage**: MinIO para armazenamento de arquivos
- **Automation**: n8n para workflows e orquestração avançada
- **LLMs**: OpenAI GPT-4o-mini para processamento e geração
- **Containers**: Docker Compose para orquestração completa

## 🚀 Instalação Rápida

### Pré-requisitos

- **Docker** e **Docker Compose**
- **OpenAI API Key** (obrigatório)
- **Git** para clone do repositório

### 1. Setup Automatizado

```bash
# Clone do repositório
git clone <repository-url>
cd rag-demo

# Execute o script de setup
chmod +x setup.sh
./setup.sh
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
- 🔧 **n8n Workflows**: http://localhost:5678 (`admin` / `admin123`)

## 📱 Funcionalidades

### 1. 📤 Upload de Documentos

- **Formatos suportados**: PDF, DOCX, TXT, MD (até 10MB)
- **Processamento automático**: LLM melhora formatação e estrutura
- **Vetorização**: Conversão para embeddings usando OpenAI
- **Armazenamento**: Documentos no MinIO, vetores no Qdrant

### 2. 🗂️ Gerenciamento de Collections

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
│   └── 📄 chat_service.py         # Serviço de chat RAG
├── 📁 templates/                   # Templates HTML
│   └── 📄 index.html              # Interface principal (SPA)
├── 📁 static/                      # Assets estáticos
│   ├── 📁 css/                    # Estilos CSS
│   ├── 📁 js/                     # JavaScript
│   └── 📁 images/                 # Imagens e ícones
├── 📁 volumes/                     # Dados persistentes
│   ├── 📁 minio/                  # Arquivos no MinIO
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
Pergunta → Embedding → Busca Qdrant → Contexto → LLM → Resposta
```

### 3. ❓ Geração Q&A
```
Documento → Chunking → LLM Generate → Q&A Pairs → Vetorização → Qdrant
```

### 4. 🔍 Busca Semântica
```
Query → Embedding → Similarity Search → Ranking → Results
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

---

**RAG-Demo** - Transformando o aprendizado de PLN com tecnologia de ponta! 🚀

> _"A melhor forma de aprender é praticando com ferramentas reais."_ 