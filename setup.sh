#!/bin/bash

# RAG-Demo Setup Script
# Este script configura o ambiente RAG-Demo para desenvolvimento e produção
# Versão: 3.0 Beta - Pronto para primeira versão pública

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    RAG-Demo Setup v3.0 Beta                 ║"
echo "║           Plataforma Educacional de PLN                     ║"
echo "║                 Versão Beta Pública                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar argumentos
DEV_MODE=false
CLEAN_MODE=false
REBUILD_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --clean)
            CLEAN_MODE=true
            shift
            ;;
        --rebuild)
            REBUILD_MODE=true
            shift
            ;;
        --help)
            echo "Uso: $0 [OPÇÕES]"
            echo ""
            echo "OPÇÕES:"
            echo "  --dev      Modo desenvolvimento (inclui todos os serviços)"
            echo "  --clean    Limpar dados existentes (pergunta sobre preservação)"
            echo "  --rebuild  Rebuild completo dos containers"
            echo "  --help     Mostrar esta ajuda"
            echo ""
            echo "EXEMPLOS:"
            echo "  $0                    # Setup padrão"
            echo "  $0 --dev             # Setup para desenvolvimento"
            echo "  $0 --clean           # Limpar dados (preserva volumes importantes)"
            echo "  $0 --clean --rebuild # Reset completo"
            echo ""
            echo "NOTAS:"
            echo "  • O modo --clean preserva automaticamente volumes com dados"
            echo "  • Volumes preservados: n8n, postgres, qdrant, minio"
            echo "  • Use --clean para gerenciar dados existentes"
            exit 0
            ;;
        *)
            log_error "Opção desconhecida: $1"
            echo "Use --help para ver as opções disponíveis"
            exit 1
            ;;
    esac
done

# Verificar ambiente e dependências do sistema
log_info "Verificando ambiente e dependências do sistema..."

# Verificar se está rodando no WSL2 (recomendado)
if [ -f /proc/version ] && grep -q microsoft /proc/version; then
    log_success "Executando no WSL2 - ambiente recomendado"
    WSL_ENVIRONMENT=true
    
    # Verificar se é WSL2 (não WSL1)
    if grep -q WSL2 /proc/version 2>/dev/null; then
        log_success "WSL2 detectado - versão correta"
    else
        log_warning "WSL1 detectado - recomendamos atualizar para WSL2"
        log_info "Para atualizar: wsl --set-version Ubuntu 2"
    fi
else
    log_info "Executando em ambiente Linux nativo"
    WSL_ENVIRONMENT=false
fi

# Verificar Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker não está instalado"
    if [ "$WSL_ENVIRONMENT" = true ]; then
        log_info "No WSL2, instale o Docker Desktop no Windows com integração WSL2"
        log_info "Guia: https://docs.docker.com/desktop/install/windows-install/"
    else
        log_info "Instale o Docker: https://docs.docker.com/get-docker/"
    fi
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose não está instalado"
    if [ "$WSL_ENVIRONMENT" = true ]; then
        log_info "Docker Compose deve vir com Docker Desktop"
        log_info "Verifique a integração WSL2 no Docker Desktop"
    else
        log_info "Instale o Docker Compose: https://docs.docker.com/compose/install/"
    fi
    exit 1
fi

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    log_error "Docker não está rodando"
    if [ "$WSL_ENVIRONMENT" = true ]; then
        log_info "Inicie o Docker Desktop no Windows"
        log_info "Verifique se a integração WSL2 está habilitada"
    else
        log_info "Inicie o Docker daemon e tente novamente"
    fi
    exit 1
fi

# Verificações específicas do WSL2
if [ "$WSL_ENVIRONMENT" = true ]; then
    log_info "Executando verificações específicas do WSL2..."
    
    # Verificar se consegue acessar localhost
    if curl -s --connect-timeout 2 http://localhost &> /dev/null; then
        log_success "Localhost acessível - configuração WSL2 correta"
    else
        log_warning "Problemas com localhost - verifique .wslconfig"
        log_info "Adicione 'localhostForwarding=true' em ~/.wslconfig"
    fi
    
    # Verificar memória disponível
    memory_gb=$(free -g | grep '^Mem:' | awk '{print $2}')
    if [ "$memory_gb" -ge 4 ]; then
        log_success "Memória disponível: ${memory_gb}GB (suficiente)"
    else
        log_warning "Memória disponível: ${memory_gb}GB (recomendado: 4GB+)"
        log_info "Configure limites de memória no arquivo .wslconfig"
    fi
fi

log_success "Dependências do sistema verificadas"

# Função para verificar se volume tem dados
check_volume_data() {
    local volume_path=$1
    local volume_name=$2
    
    if [ -d "$volume_path" ] && [ "$(ls -A "$volume_path" 2>/dev/null)" ]; then
        local size=$(du -sh "$volume_path" 2>/dev/null | cut -f1)
        log_warning "Volume $volume_name contém dados existentes ($size)"
        return 0
    else
        return 1
    fi
}

# Função para preservar volume
preserve_volume() {
    local volume_path=$1
    local volume_name=$2
    
    if check_volume_data "$volume_path" "$volume_name"; then
        read -p "Preservar dados do $volume_name? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Removendo dados do $volume_name..."
            rm -rf "$volume_path"/*
            return 1
        else
            log_success "Dados do $volume_name serão preservados"
            return 0
        fi
    fi
    return 1
}

# Limpeza se solicitada
if [ "$CLEAN_MODE" = true ]; then
    log_warning "Modo limpeza ativado - dados existentes serão removidos"
    read -p "Tem certeza que deseja continuar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Operação cancelada"
        exit 0
    fi
    
    log_info "Parando containers..."
    docker-compose down --remove-orphans 2>/dev/null || true
    
    log_info "Verificando volumes existentes..."
    
    # Verificar e preservar volumes importantes
    volumes_to_preserve=()
    
    if preserve_volume "volumes/n8n" "n8n"; then
        volumes_to_preserve+=("n8n")
    fi
    
    if preserve_volume "volumes/postgres" "PostgreSQL"; then
        volumes_to_preserve+=("postgres")
    fi
    
    if preserve_volume "volumes/qdrant" "Qdrant"; then
        volumes_to_preserve+=("qdrant")
    fi
    
    if preserve_volume "volumes/minio" "MinIO"; then
        volumes_to_preserve+=("minio")
    fi
    
    # Resumo dos volumes preservados
    if [ ${#volumes_to_preserve[@]} -gt 0 ]; then
        log_info "Volumes preservados: ${volumes_to_preserve[*]}"
    else
        log_info "Nenhum volume será preservado"
    fi
    
    # Limpar volumes Docker não utilizados
    log_info "Limpando volumes Docker não utilizados..."
    docker volume prune -f 2>/dev/null || true
    
    log_info "Limpando cache Python..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    log_info "Limpando diretório uploads..."
    rm -rf uploads 2>/dev/null || true
    
    log_success "Limpeza concluída"
fi

# Rebuild se solicitado
if [ "$REBUILD_MODE" = true ]; then
    log_info "Rebuilding containers..."
    if grep -qiE '^[[:space:]]*GLINER_TRAIN[[:space:]]*=[[:space:]]*(true|1|yes)[[:space:]]*$' .env 2>/dev/null; then
        docker compose --profile gliner-train build --no-cache
    elif grep -qiE '^[[:space:]]*GLINER_BERT[[:space:]]*=[[:space:]]*(true|1|yes)[[:space:]]*$' .env 2>/dev/null; then
        docker compose --profile gliner build --no-cache
    else
        docker compose build --no-cache
    fi
    log_success "Rebuild concluído"
fi

# Criar diretórios necessários
log_info "Criando estrutura de diretórios..."

# Função para criar diretório com permissões adequadas
create_directory_with_permissions() {
    local dir_path=$1
    local owner_uid=${2:-1000}
    local owner_gid=${3:-1000}
    
    if [ ! -d "$dir_path" ]; then
        if command -v sudo &> /dev/null; then
            sudo mkdir -p "$dir_path" 2>/dev/null || {
                log_warning "Não foi possível criar $dir_path com sudo, tentando sem..."
                mkdir -p "$dir_path" 2>/dev/null || {
                    log_error "Falha ao criar diretório: $dir_path"
                    return 1
                }
            }
            sudo chown -R "$owner_uid:$owner_gid" "$dir_path" 2>/dev/null || {
                log_warning "Não foi possível alterar permissões de $dir_path"
            }
        else
            mkdir -p "$dir_path" 2>/dev/null || {
                log_error "Falha ao criar diretório: $dir_path"
                return 1
            }
            chown -R "$owner_uid:$owner_gid" "$dir_path" 2>/dev/null || {
                log_warning "Não foi possível alterar permissões de $dir_path"
            }
        fi
    else
        # Diretório já existe, apenas corrigir permissões
        if command -v sudo &> /dev/null; then
            sudo chown -R "$owner_uid:$owner_gid" "$dir_path" 2>/dev/null || {
                log_warning "Não foi possível alterar permissões de $dir_path existente"
            }
        else
            chown -R "$owner_uid:$owner_gid" "$dir_path" 2>/dev/null || {
                log_warning "Não foi possível alterar permissões de $dir_path existente"
            }
        fi
    fi
}

# Função para corrigir permissões dos volumes Docker
fix_volume_permissions() {
    log_info "Corrigindo permissões dos volumes Docker..."
    
    # N8N - usuário node (UID 1000)
    if [ -d "volumes/n8n" ]; then
        log_info "Configurando permissões do N8N (UID 1000)..."
        if command -v sudo &> /dev/null; then
            sudo chown -R 1000:1000 volumes/n8n 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do N8N"
            }
        else
            chown -R 1000:1000 volumes/n8n 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do N8N"
            }
        fi
        log_success "Permissões do N8N configuradas"
    fi
    
    # PostgreSQL - usuário postgres (UID 70)
    if [ -d "volumes/postgres" ]; then
        log_info "Configurando permissões do PostgreSQL (UID 70)..."
        if command -v sudo &> /dev/null; then
            sudo chown -R 70:70 volumes/postgres 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do PostgreSQL"
            }
        else
            chown -R 70:70 volumes/postgres 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do PostgreSQL"
            }
        fi
        log_success "Permissões do PostgreSQL configuradas"
    fi
    
    # Qdrant - usuário padrão (UID 1000)
    if [ -d "volumes/qdrant" ]; then
        log_info "Configurando permissões do Qdrant (UID 1000)..."
        if command -v sudo &> /dev/null; then
            sudo chown -R 1000:1000 volumes/qdrant 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do Qdrant"
            }
        else
            chown -R 1000:1000 volumes/qdrant 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do Qdrant"
            }
        fi
        log_success "Permissões do Qdrant configuradas"
    fi
    
    # MinIO - usuário padrão (UID 1000)
    if [ -d "volumes/minio" ]; then
        log_info "Configurando permissões do MinIO (UID 1000)..."
        if command -v sudo &> /dev/null; then
            sudo chown -R 1000:1000 volumes/minio 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do MinIO"
            }
        else
            chown -R 1000:1000 volumes/minio 2>/dev/null || {
                log_warning "Não foi possível corrigir permissões do MinIO"
            }
        fi
        log_success "Permissões do MinIO configuradas"
    fi
    
    log_success "Permissões dos volumes corrigidas"
}

# Criar diretórios principais
create_directory_with_permissions "uploads"
create_directory_with_permissions "volumes/minio" 1000 1000
create_directory_with_permissions "volumes/qdrant" 1000 1000
create_directory_with_permissions "volumes/n8n" 1000 1000
create_directory_with_permissions "volumes/postgres" 70 70
create_directory_with_permissions "volumes/huggingface" 1000 1000
create_directory_with_permissions "volumes/gliner-checkpoints" 1000 1000
create_directory_with_permissions "static/css"
create_directory_with_permissions "static/js"
create_directory_with_permissions "static/images"
create_directory_with_permissions "src"
create_directory_with_permissions "templates"
create_directory_with_permissions "scripts"
create_directory_with_permissions "docs"

# Corrigir permissões dos volumes (importante para Docker)
fix_volume_permissions

# Garantir encryptionKey do n8n no host (volumes/n8n/config)
log_info "Garantindo encryptionKey do n8n..."
if [ -f "scripts/ensure-n8n-encryption-key.sh" ]; then
    chmod +x scripts/ensure-n8n-encryption-key.sh || true
    bash scripts/ensure-n8n-encryption-key.sh
else
    log_warning "scripts/ensure-n8n-encryption-key.sh não encontrado. Criando rapidamente..."
    mkdir -p scripts
    cat > scripts/ensure-n8n-encryption-key.sh << 'EOS'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
N8N_DIR="$ROOT_DIR/volumes/n8n"
CONFIG_FILE="$N8N_DIR/config"
mkdir -p "$N8N_DIR"
if [[ -f "$CONFIG_FILE" ]]; then
  if jq -e . "$CONFIG_FILE" >/dev/null 2>&1; then
    echo "🔐 Mantendo encryptionKey existente em $CONFIG_FILE"
    exit 0
  else
    cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%s)" || true
  fi
fi
KEY="$(openssl rand -base64 24)"
cat > "$CONFIG_FILE" <<JSON
{
  "encryptionKey": "$KEY"
}
JSON
chmod 600 "$CONFIG_FILE" || true
echo "✅ Gerado $CONFIG_FILE com encryptionKey estável."
EOS
    chmod +x scripts/ensure-n8n-encryption-key.sh
    bash scripts/ensure-n8n-encryption-key.sh
fi

# Garantir permissões seguras do arquivo de configuração do n8n
if [ -f "volumes/n8n/config" ]; then
    chmod 600 volumes/n8n/config 2>/dev/null || true
fi

# Verificar se todos os diretórios foram criados
log_info "Verificando diretórios criados..."
required_dirs=("uploads" "volumes/minio" "volumes/qdrant" "volumes/n8n" "volumes/postgres" "volumes/huggingface" "volumes/gliner-checkpoints" "static/css" "static/js" "static/images" "src" "templates" "scripts" "docs")

for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        log_success "✓ $dir"
    else
        log_error "✗ $dir - não foi criado"
    fi
done

log_success "Diretórios criados e permissões configuradas"

if check_volume_data "volumes/n8n" "n8n"; then
    volumes_with_data+=("n8n")
fi

if check_volume_data "volumes/postgres" "PostgreSQL"; then
    volumes_with_data+=("postgres")
fi

if check_volume_data "volumes/qdrant" "Qdrant"; then
    volumes_with_data+=("qdrant")
fi

if check_volume_data "volumes/minio" "MinIO"; then
    volumes_with_data+=("minio")
fi

if [ ${#volumes_with_data[@]} -gt 0 ]; then
    log_info "Volumes com dados existentes: ${volumes_with_data[*]}"
    log_info "Use --clean para gerenciar esses dados"
else
    log_success "Nenhum volume com dados existentes encontrado"
fi

# Verificar/criar arquivo .env
if [ ! -f .env ]; then
    log_info "Criando arquivo .env..."
    if [ -f env.example ]; then
        cp env.example .env
        log_success "Arquivo .env criado a partir de env.example"
    else
        log_warning "env.example não encontrado, criando .env básico"
        cat > .env << 'EOF'
# OpenAI (Obrigatório)
OPENAI_API_KEY=

# Google Gemini (Opcional)
GEMINI_API_KEY=

# Modelo para geração de Q&A
MODEL_QA_GENERATOR=gpt-4o-mini

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=documents

# PostgreSQL - Memória do Chat
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=chat_memory
POSTGRES_USER=chat_user
POSTGRES_PASSWORD=chat_password

# n8n
N8N_WEBHOOK_URL=http://localhost:5678/webhook-test/2d388a36-490f-4dfd-952a-6c5c63dac146
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=admin123

# Flask
FLASK_ENV=production
FLASK_DEBUG=false

# Embedding
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small

# Processamento
CHUNK_SIZE=1000
CHUNK_OVERLAP=200

# Diretórios
UPLOAD_FOLDER=uploads
DATA_FOLDER=data
EOF
    fi
    
    log_warning "Configure sua OPENAI_API_KEY no arquivo .env antes de continuar"
    log_info "Editando .env..."
    
    # Tentar abrir editor
    if command -v nano &> /dev/null; then
        nano .env
    elif command -v vim &> /dev/null; then
        vim .env
    elif command -v code &> /dev/null; then
        code .env
    else
        log_warning "Editor não encontrado. Edite .env manualmente"
        echo "echo 'OPENAI_API_KEY=sua-chave-aqui' >> .env"
    fi
fi

# Carregar e validar variáveis de ambiente
log_info "Validando configuração..."

if [ -f .env ]; then
    source .env
fi

# Verificar OPENAI_API_KEY
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your-openai-api-key-here" ]; then
    log_error "OPENAI_API_KEY não está configurada no .env"
    log_info "Obtenha sua chave em: https://platform.openai.com/api-keys"
    exit 1
fi

# Validar formato da chave OpenAI
if [[ ! "$OPENAI_API_KEY" =~ ^sk-[a-zA-Z0-9]{48,}$ ]]; then
    log_warning "Formato da OPENAI_API_KEY pode estar incorreto"
    log_info "Chaves OpenAI começam com 'sk-' seguido de 48+ caracteres"
fi

# Verificar GEMINI_API_KEY (opcional)
if [ -n "$GEMINI_API_KEY" ] && [ "$GEMINI_API_KEY" != "your-key-here" ]; then
    log_success "GEMINI_API_KEY configurada (opcional)"
else
    log_warning "GEMINI_API_KEY não configurada (opcional - usado como fallback)"
fi

log_success "Configuração validada"

# Verificar arquivos essenciais
log_info "Verificando arquivos do projeto..."

essential_files=("app.py" "docker-compose.yml" "requirements.txt")
for file in "${essential_files[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Arquivo essencial não encontrado: $file"
        exit 1
    fi
done

# Verificar scripts do PostgreSQL
if [ ! -f "scripts/init-postgres.sql" ]; then
    log_warning "Script de inicialização do PostgreSQL não encontrado"
    log_info "Criando script básico..."
    mkdir -p scripts
    cat > scripts/init-postgres.sql << 'EOF'
-- Script básico de inicialização do PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);

GRANT ALL PRIVILEGES ON TABLE chat_messages TO chat_user;
EOF
fi

# Verificar e tornar executável o script de setup do PostgreSQL
if [ -f "scripts/setup-postgres.sh" ]; then
    chmod +x scripts/setup-postgres.sh
    log_success "Script setup-postgres.sh configurado como executável"
fi

# Verificar e tornar executável o script de teste do PostgreSQL
if [ -f "scripts/test-postgres-connection.py" ]; then
    chmod +x scripts/test-postgres-connection.py
    log_success "Script test-postgres-connection.py configurado como executável"
fi

log_success "Arquivos do projeto verificados"

# GLiNER + BERTimbau: profile opcional (não sobe no compose padrão)
gliner_bert_enabled() {
    [ -f .env ] || return 1
    grep -qiE '^[[:space:]]*GLINER_BERT[[:space:]]*=[[:space:]]*(true|1|yes)[[:space:]]*$' .env
}

gliner_train_enabled() {
    [ -f .env ] || return 1
    grep -qiE '^[[:space:]]*GLINER_TRAIN[[:space:]]*=[[:space:]]*(true|1|yes)[[:space:]]*$' .env
}

COMPOSE_PROFILE_ARGS=()
GLINER_COMPOSE_SERVICE=""
if gliner_train_enabled; then
    COMPOSE_PROFILE_ARGS=(--profile gliner-train)
    GLINER_COMPOSE_SERVICE="gliner-bert-gpu"
    log_info "GLiNER/BERTimbau: profile gliner-train ativo (GPU, JSON BIO)"
elif gliner_bert_enabled; then
    COMPOSE_PROFILE_ARGS=(--profile gliner)
    GLINER_COMPOSE_SERVICE="gliner-bert"
    log_info "GLiNER/BERTimbau: profile gliner ativo (GLINER_BERT=true)"
else
    log_info "GLiNER/BERTimbau: omitido (GLINER_BERT=true para inferência; GLINER_TRAIN=true para GPU)"
fi

# Preparar docker-compose baseado no modo
COMPOSE_FILE="docker-compose.yml"

if [ "$DEV_MODE" = true ]; then
    log_info "Modo desenvolvimento ativado"
    # Criar docker-compose override para desenvolvimento
    cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  rag-demo-app:
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=true
    volumes:
      - ./src:/app/src:cached
      - ./templates:/app/templates:cached
      - ./static:/app/static:cached
    ports:
      - "5000:5000"
EOF
    log_success "Configuração de desenvolvimento criada (com n8n ativo)"
else
    # Remover override se existir
    rm -f docker-compose.override.yml 2>/dev/null || true
fi

# Iniciar serviços
log_info "Iniciando serviços Docker..."

if [ "$DEV_MODE" = true ]; then
    if [ -n "$GLINER_COMPOSE_SERVICE" ]; then
        docker compose "${COMPOSE_PROFILE_ARGS[@]}" up -d qdrant minio postgres n8n rag-demo-app "$GLINER_COMPOSE_SERVICE"
    else
        docker compose up -d qdrant minio postgres n8n rag-demo-app
    fi
    log_info "Serviços iniciados em modo desenvolvimento (incluindo PostgreSQL e n8n)"
else
    docker compose "${COMPOSE_PROFILE_ARGS[@]}" up -d
    log_info "Todos os serviços iniciados"
fi

# Aguardar inicialização
log_info "Aguardando serviços ficarem prontos..."
sleep 10

# Corrigir permissões após inicialização dos containers
log_info "Corrigindo permissões após inicialização dos containers..."
fix_volume_permissions

# Função para verificar saúde dos serviços
check_service() {
    local name=$1
    local url=$2
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f "$url" &> /dev/null; then
            log_success "$name está respondendo"
            return 0
        fi
        
        if [ $((attempt % 5)) -eq 0 ]; then
            log_info "Aguardando $name... (tentativa $attempt/$max_attempts)"
        fi
        
        sleep 2
        ((attempt++))
    done
    
    log_error "$name não está respondendo após ${max_attempts} tentativas"
    return 1
}

# Verificar serviços
log_info "Verificando saúde dos serviços..."

check_service "Qdrant" "http://localhost:6333/collections"
check_service "MinIO" "http://localhost:9000/minio/health/live"

# Verificar PostgreSQL
log_info "Verificando PostgreSQL..."
sleep 5  # PostgreSQL demora um pouco para inicializar
if docker-compose exec postgres pg_isready -U chat_user -d chat_memory &> /dev/null; then
    log_success "PostgreSQL está rodando"
else
    log_warning "PostgreSQL ainda está inicializando (normal)"
fi

check_service "RAG-Demo App" "http://localhost:5000/api/test"

# Verificar n8n (em desenvolvimento e produção)
log_info "Verificando n8n (pode demorar mais)..."
n8n_ready=false
for i in {1..6}; do
    sleep 10
    if curl -f "http://localhost:5678" &> /dev/null; then
        log_success "n8n está rodando"
        n8n_ready=true
        break
    else
        log_info "Aguardando n8n... (tentativa $i/6)"
    fi
done

if [ "$n8n_ready" = false ]; then
    log_warning "n8n ainda está inicializando (normal para primeira execução)"
    log_info "Acesse http://localhost:5678 em alguns minutos"
fi

# Executar verificações adicionais
log_info "Executando verificações adicionais..."

# Verificar se consegue listar collections
if curl -f "http://localhost:5000/api/collections" &> /dev/null; then
    log_success "API de collections funcionando"
else
    log_warning "API de collections pode não estar pronta"
fi

# Verificar se consegue acessar Qdrant
if curl -f "http://localhost:6333/collections" &> /dev/null; then
    log_success "Qdrant API funcionando"
else
    log_warning "Qdrant API pode não estar pronta"
fi

# Verificar PostgreSQL (teste de conexão)
log_info "Testando conexão com PostgreSQL..."
if [ -f "scripts/test-postgres-connection.py" ]; then
    # Aguardar um pouco mais para o PostgreSQL inicializar completamente
    sleep 10
    if python scripts/test-postgres-connection.py &> /dev/null; then
        log_success "PostgreSQL - teste de conexão passou"
    else
        log_warning "PostgreSQL - teste de conexão falhou (pode estar inicializando)"
        log_info "Você pode testar manualmente com: python scripts/test-postgres-connection.py"
    fi
else
    log_warning "Script de teste PostgreSQL não encontrado"
    log_info "Para testar PostgreSQL manualmente, execute: docker-compose exec postgres psql -U chat_user -d chat_memory"
fi

# Resultados finais
echo ""
log_success "RAG-Demo está pronto!"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                      URLs de Acesso                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  🌐 RAG-Demo:        http://localhost:5000                  ║"
echo "║  🔍 Qdrant:          http://localhost:6333/dashboard        ║"
echo "║  📦 MinIO:           http://localhost:9001                  ║"
echo "║  🗄️  PostgreSQL:      localhost:5432                        ║"
echo "║  🔧 n8n:             http://localhost:5678                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}"
echo "🔑 Credenciais:"
echo "   • MinIO: minioadmin / minioadmin"
echo "   • PostgreSQL: chat_user / chat_password"
echo "   • n8n: admin / admin123"
echo -e "${NC}"

echo -e "${YELLOW}"
echo "📚 Próximos passos:"
echo "   1. Acesse http://localhost:5000"
echo "   2. Configure workflows no n8n (http://localhost:5678)"
echo "   3. Configure credenciais PostgreSQL no n8n"
echo "   4. Use o Postgres Chat Memory node nos workflows"
echo "   5. Crie uma nova collection"
echo "   6. Faça upload de um documento"
echo "   7. Teste o gerador de Q&A"
echo "   8. Experimente o chat RAG"
echo -e "${NC}"

# Comandos úteis
echo -e "${BLUE}"
echo "🛠️  Comandos úteis:"
echo "   • Ver logs:           docker-compose logs -f"
echo "   • Parar serviços:     docker-compose down"
echo "   • Testar PostgreSQL:  python scripts/test-postgres-connection.py"
echo "   • Setup PostgreSQL:   ./scripts/setup-postgres.sh"
echo "   • Reset completo:     $0 --clean --rebuild"
if [ "$DEV_MODE" = true ]; then
echo "   • Modo produção:      $0"
else
echo "   • Modo desenvolvimento: $0 --dev"
fi
echo -e "${NC}"

# Verificar se há warnings
if docker-compose ps | grep -q "unhealthy\|exited"; then
    echo ""
    log_warning "Alguns serviços podem ter problemas:"
    docker-compose ps
    echo ""
    log_info "Execute 'docker-compose logs [serviço]' para investigar"
fi

# Informações específicas da versão beta
echo ""
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    🎉 VERSÃO BETA v3.0                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

log_info "📖 Informações sobre PostgreSQL:"
echo "   • O PostgreSQL está configurado como memória do chat para o n8n"
echo "   • Database: chat_memory"
echo "   • Tabela principal: chat_messages"
echo "   • Para mais detalhes, consulte: docs/postgres-chat-memory.md"

echo ""
log_info "🔧 Informações sobre n8n:"
echo "   • Versão estável: latest (com correções de permissões)"
echo "   • Permissões configuradas automaticamente (UID 1000)"
echo "   • Primeiro acesso pode demorar 2-3 minutos"
echo "   • Acesso: http://localhost:5678 (admin/admin123)"
echo "   • Volumes persistidos em ./volumes/n8n/"

echo ""
log_info "🗄️ Informações sobre PostgreSQL:"
echo "   • Permissões configuradas automaticamente (UID 70)"
echo "   • Volumes persistidos em ./volumes/postgres/"
echo "   • Database: chat_memory"
echo "   • Tabela principal: chat_messages"
echo "   • Para mais detalhes, consulte: docs/postgres-chat-memory.md"

echo ""
log_info "🆕 Novidades da versão Beta:"
echo "   • ✅ Suporte completo ao WSL2 + Docker Desktop"
echo "   • ✅ Verificações automáticas de ambiente"
echo "   • ✅ Sistema de sessões de chat aprimorado"
echo "   • ✅ Interface web otimizada e responsiva"
echo "   • ✅ Integração completa com n8n workflows"
echo "   • ✅ PostgreSQL configurado automaticamente"
echo "   • ✅ Suporte a múltiplos modelos de embedding"
echo "   • ✅ Correção automática de permissões dos volumes"
echo "   • ✅ Bind mounts para persistência de dados"

echo ""
log_info "🔧 Para desenvolvimento:"
echo "   • Execute: ./setup.sh --dev (inclui hot-reload)"
echo "   • Logs em tempo real: docker-compose logs -f"
echo "   • Reset completo: ./setup.sh --clean --rebuild"

echo ""
log_info "🌐 Ambiente WSL2 detectado:" 
if [ "$WSL_ENVIRONMENT" = true ]; then
echo "   • ✅ Configuração otimizada para Windows + WSL2"
echo "   • ✅ Docker Desktop integração verificada"
echo "   • 💡 Dica: Configure .wslconfig para melhor performance"
else
echo "   • ℹ️  Executando em ambiente Linux nativo"
fi

echo ""
log_info "📧 Suporte e Feedback:"
echo "   • 🐛 Reporte bugs via GitHub Issues"
echo "   • 💡 Sugestões são bem-vindas"
echo "   • 📚 Documentação completa no README.md"
echo ""

log_success "🎯 RAG-Demo Beta está pronto para uso! Bom aprendizado! 🚀" 