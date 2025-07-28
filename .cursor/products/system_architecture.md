# Documento de Especificação de Requisitos de Software – App RAG-Demo

## Projeto do Sistema

O RAG-Demo é uma aplicação educacional baseada em RAG (Recuperação Aumentada por Geração), composta por:

- Frontend web leve (SPA) com três abas: Upload, Editor de Conteúdo, Chat.
- Backend mínimo em Python (FastAPI) apenas para roteamento de arquivos e fallback do chat.
- Orquestração das tarefas via **n8n**: extração de texto, vetorização, armazenamento em Qdrant, geração de sessões.
- Armazenamento de arquivos no **MinIO**.
- Vetores persistidos no **Qdrant**, separados por modelo e tema.

## Padrão de Arquitetura

- Arquitetura orientada a serviços (microserviços via Docker Compose).
- Orquestração de tarefas assíncronas com **n8n** (low-code).
- API Gateway simples via FastAPI (somente quando não for possível via n8n).
- Frontend estático consumindo Web APIs.

## Gerenciamento de Estado

- Sessões de chat e status de vetorização armazenados localmente no frontend (cache) e sincronizados com backend/n8n via polling ou WebSocket.
- Histórico de sessões mantido em arquivo JSON ou no próprio n8n (Data Store node).
- State mínimo no frontend (preferencialmente sem frameworks complexos como Redux).

## Fluxo de Dados

1. Usuário envia PDF via frontend → Frontend envia para n8n (Webhook).
2. n8n processa (OCR se necessário), converte para Markdown → salva no MinIO.
3. Texto convertido → enviado ao serviço de vetorização (Python ou serviço externo) → vetores enviados ao Qdrant.
4. Ao iniciar o chat, frontend consulta n8n para buscar contexto → envia consulta → resposta gerada com base nos vetores.
5. Editor de perguntas/respostas permite vetorização manual (fluxo idêntico ao upload).

## Pilha Técnica

- **Frontend**: HTML5, JavaScript (Vanilla ou Alpine.js), Tailwind CSS.
- **Backend (mínimo)**: Python 3.12, FastAPI (somente se n8n não for suficiente).
- **Orquestração**: [n8n](https://n8n.io)
- **Vetorização**: Python (LangChain + Embedding Models)
- **Banco Vetorial**: [Qdrant](https://qdrant.tech)
- **Armazenamento**: MinIO (S3-compatible)
- **Deploy**: Docker Compose
- **Outros**: WebSocket ou polling para feedback ao usuário

## Processo de Autenticação

- **Sem autenticação**. Uso local em laboratório.
- Acesso direto ao frontend em localhost.
- URLs protegidas por isolamento de rede local.

## Projeto de Rotas

### Frontend (SPA)

- `/` → Aba de Upload
- `/editor` → Aba Editor de Conteúdo
- `/chat` → Aba Chat com sessão ativa

### Webhooks n8n

- `POST /upload-document` → Recebe arquivo PDF
- `POST /vectorize-md` → Recebe conteúdo markdown
- `POST /query-chat` → Consulta com vetor e histórico
- `GET /sessions` → Lista sessões anteriores

## Projeto de APIs

Preferencialmente via **n8n Webhooks**:

- `POST /upload-document`
  - Entrada: PDF, modelo de embedding, tema
  - Saída: status da vetorização

- `POST /vectorize-md`
  - Entrada: markdown com metadados
  - Saída: confirmação

- `POST /query-chat`
  - Entrada: texto da pergunta + sessão
  - Saída: resposta gerada com base nos vetores

- `GET /sessions`
  - Entrada: n/a
  - Saída: lista de sessões disponíveis

## Projeto de Banco de Dados (DER)

Sem banco relacional tradicional. Estrutura de dados baseada em:

- **Qdrant**
  - Collections nomeadas por modelo e tema
  - Cada vetor com metadados: `source`, `timestamp`, `tipo (upload/manual)`

- **MinIO**
  - Bucket `documents/`
    - `originals/{tema}/{arquivo}.pdf`
    - `converted/{tema}/{arquivo}.md`

- **n8n Data Store (opcional)**
  - JSON com sessões de chat:
    ```json
    {
      "sessao_id": "abc123",
      "mensagens": [
        {"usuario": "Aluno", "texto": "..."},
        {"assistente": "RAG", "texto": "..."}
      ]
    }
    ```

## Projeto de implantação (containers)

A aplicação é implantada localmente via Docker Compose com os seguintes serviços:

```yaml
version: '3.8'

services:
  # Qdrant Vector Database
  qdrant:
    container_name: qdrant
    image: qdrant/qdrant:v1.7.3
    ports:
      - "6333:6333"  # HTTP API
      - "6334:6334"  # gRPC API
    volumes:
      - ./volumes/qdrant:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 20s
      retries: 3

  # MinIO para armazenamento de arquivos
  minio:
    container_name: minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ./volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # n8n - Orquestração de Workflows
  n8n:
    container_name: n8n
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin123
      - N8N_HOST=localhost
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - WEBHOOK_URL=http://localhost:5678/
      - GENERIC_TIMEZONE=America/Sao_Paulo
    volumes:
      - ./volumes/n8n:/home/node/.n8n
