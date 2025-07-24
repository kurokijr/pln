# Documento de Especificação de Requisitos de Software – App RAG-Demo

## Projeto do Sistema

O RAG-Demo é uma aplicação educacional baseada em RAG (Recuperação Aumentada por Geração), composta por:

- Frontend web leve (SPA) com três abas: Upload, Editor de Conteúdo, Chat.
- Backend mínimo em Python (FastAPI) apenas para roteamento de arquivos e fallback do chat.
- Orquestração das tarefas via **n8n**: extração de texto, vetorização, armazenamento em Milvus, geração de sessões.
- Armazenamento de arquivos no **MinIO**.
- Vetores persistidos no **Milvus**, separados por modelo e tema.

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
3. Texto convertido → enviado ao serviço de vetorização (Python ou serviço externo) → vetores enviados ao Milvus.
4. Ao iniciar o chat, frontend consulta n8n para buscar contexto → envia consulta → resposta gerada com base nos vetores.
5. Editor de perguntas/respostas permite vetorização manual (fluxo idêntico ao upload).

## Pilha Técnica

- **Frontend**: HTML5, JavaScript (Vanilla ou Alpine.js), Tailwind CSS.
- **Backend (mínimo)**: Python 3.12, FastAPI (somente se n8n não for suficiente).
- **Orquestração**: [n8n](https://n8n.io)
- **Vetorização**: Python (LangChain + Embedding Models)
- **Banco Vetorial**: [Milvus](https://milvus.io) + [Attu](https://github.com/zilliztech/attu)
- **Armazenamento**: MinIO (S3-compatible)
- **Deploy**: Docker Compose
- **Outros**: etcd (para Milvus), WebSocket ou polling para feedback ao usuário

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

- **Milvus**
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
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  standalone:
    container_name: milvus-standalone
    hostname: milvushost
    image: milvusdb/milvus:v2.3.11
    command: ["milvus", "run", "standalone"]
    security_opt:
      - seccomp:unconfined
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
      interval: 30s
      start_period: 90s
      timeout: 20s
      retries: 3
    depends_on:
      - etcd
      - minio

  gui:
    container_name: milvus-gui
    image: zilliz/attu:latest
    environment:
      HOST_URL: http://localhost:8000
      MILVUS_URL: standalone:19530
    ports:
      - "8000:3000"
    depends_on_
