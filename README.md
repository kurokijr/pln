# RAG-Demo - Ambiente Educacional

Uma aplicação educacional desenvolvida para demonstrar o funcionamento integrado de uma arquitetura baseada em Recuperação Aumentada por Geração (RAG), utilizando serviços modernos como Milvus, MinIO, n8n e LLMs.

## 🎯 Objetivo

O RAG-Demo é voltado para alunos da disciplina de Processamento de Linguagem Natural (PLN), permitindo que experimentem de forma prática:

- Upload e processamento de documentos PDF/DOCX
- Vetorização usando modelos de embedding modernos (APIs)
- Armazenamento vetorial com Milvus
- Chat RAG com múltiplas sessões
- Geração automática de perguntas e respostas
- Interface web moderna e responsiva

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │   Milvus        │
│   (HTML/JS)     │◄──►│   (Python)      │◄──►│   (Vectors)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MinIO         │    │   OpenAI        │    │   Grok          │
│   (Storage)     │    │   (LLMs)        │    │   (LLMs)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Componentes Principais

- **Frontend**: Interface web moderna com Tailwind CSS
- **Backend**: Flask com APIs REST
- **Vector Store**: Milvus (única fonte de dados)
- **Storage**: MinIO para arquivos
- **Orchestration**: n8n para workflows complexos
- **LLMs**: OpenAI GPT e Grok para processamento e geração

## 🚀 Instalação e Configuração

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12+
- OpenAI API Key

### 1. Clone o repositório

```bash
git clone <repository-url>
cd rag-demo
```

### 2. Configure as variáveis de ambiente

```bash
cp env.example .env
```

Edite o arquivo `.env` com suas configurações:

```env
# OpenAI
OPENAI_API_KEY=your-openai-api-key-here

# Outras configurações...
```

### 3. Execute com Docker Compose

```bash
docker-compose up -d
```

### 4. Acesse a aplicação

- **RAG-Demo**: http://localhost:5000
- **Attu (Milvus GUI)**: http://localhost:8000
- **MinIO Console**: http://localhost:9001
- **n8n**: http://localhost:5678

## 📚 Funcionalidades

### 1. Upload de Documentos

- Suporte para PDF, DOCX, TXT e MD
- Processamento automático com LLMs para melhorar formatação
- Vetorização usando modelos de API (OpenAI, Grok)
- Armazenamento direto no Milvus

### 2. Gerenciamento de Collections

- **Criação direta**: Collections criadas diretamente no Milvus
- **Múltiplos modelos**: Suporte a diferentes modelos de embedding:
  - OpenAI Text Embedding (1536d)
  - Grok Embedding (384d)
- **Validação**: Prevenção de mistura de embeddings diferentes
- **Interface visual**: Gerenciamento completo via interface web

### 3. Editor de Conteúdo

- Editor Markdown com preview
- Geração automática de perguntas e respostas
- Vetorização manual de conteúdo
- Configuração de parâmetros (dificuldade, número de QAs)

### 4. Chat RAG

- Múltiplas sessões de conversa
- Busca semântica em documentos vetorizados
- Respostas baseadas em contexto
- Histórico persistente

## 🔧 APIs Disponíveis

### Collections
- `GET /api/collections` - Listar collections do Milvus
- `POST /api/collections` - Criar nova collection
- `DELETE /api/collections/{name}` - Deletar collection

### Databases
- `GET /api/databases` - Listar databases do Milvus

### Upload e Processamento
- `POST /api/upload` - Upload e vetorização de documentos
- `POST /api/qa-generate` - Gerar perguntas e respostas

### Chat
- `POST /api/chat` - Processar mensagem de chat
- `GET /api/sessions` - Listar sessões
- `POST /api/sessions` - Criar nova sessão
- `DELETE /api/sessions/{id}` - Deletar sessão

### Configuração
- `GET /api/embedding-models` - Listar modelos disponíveis

## 🛠️ Troubleshooting

### Problemas Comuns

1. **Milvus não conecta**
   ```bash
   # Verificar se o serviço está rodando
   docker-compose ps
   
   # Reiniciar Milvus
   docker-compose restart standalone
   ```

2. **OpenAI API Key inválida**
   ```bash
   # Verificar variável de ambiente
   echo $OPENAI_API_KEY
   ```

3. **Erro de permissão no MinIO**
   ```bash
   # Verificar credenciais
   docker-compose logs minio
   ```

### Logs de Debug

```python
# Habilitar logs detalhados
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Estrutura do Projeto

```
📦 RAG-Demo/
├── 📁 src/                         # Código fonte
│   ├── 📄 config.py               # Configurações
│   ├── 📄 vector_store.py         # Interface Milvus
│   ├── 📄 document_processor.py   # Processamento de documentos
│   ├── 📄 storage.py              # Gerenciamento MinIO
│   └── 📄 chat_service.py         # Serviço de chat
├── 📁 templates/                   # Templates HTML
├── 📁 uploads/                     # Arquivos temporários
├── 📁 volumes/                     # Dados persistentes
│   ├── 📁 minio/                   # Arquivos no MinIO
│   ├── 📁 milvus/                  # Vetores no Milvus
│   └── 📁 n8n/                     # Workflows n8n
├── 📄 app.py                       # Aplicação Flask
├── 📄 docker-compose.yml           # Configuração Docker
├── 📄 requirements.txt             # Dependências Python
└── 📄 README.md                    # Documentação
```

## 🔄 Fluxo de Dados

1. **Upload**: Arquivo → Processamento → Vetorização → Milvus
2. **Chat**: Pergunta → Busca no Milvus → Geração de resposta
3. **Q&A**: Texto → Geração → Vetorização (opcional) → Milvus

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está licenciado sob a MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 🙏 Agradecimentos

- [Milvus](https://milvus.io/) - Vector Database
- [MinIO](https://min.io/) - Object Storage
- [n8n](https://n8n.io/) - Workflow Automation
- [OpenAI](https://openai.com/) - Language Models
- [LangChain](https://langchain.com/) - LLM Framework

## 📞 Suporte

Para dúvidas ou problemas:

1. Verifique a documentação
2. Consulte os logs de erro
3. Abra uma issue no GitHub
4. Entre em contato com a equipe de desenvolvimento

---

**RAG-Demo** - Transformando o aprendizado de PLN com tecnologia de ponta! 🚀 