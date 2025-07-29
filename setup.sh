#!/bin/bash

# RAG-Demo Setup Script
# Este script configura o ambiente RAG-Demo para desenvolvimento e produção
# Versão: 2.0

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
echo "║                    RAG-Demo Setup v2.0                      ║"
echo "║           Plataforma Educacional de PLN                     ║"
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
            echo "  --dev      Modo desenvolvimento (não inicia n8n)"
            echo "  --clean    Limpar dados existentes antes de iniciar"
            echo "  --rebuild  Rebuild completo dos containers"
            echo "  --help     Mostrar esta ajuda"
            echo ""
            echo "EXEMPLOS:"
            echo "  $0                    # Setup padrão"
            echo "  $0 --dev             # Setup para desenvolvimento"
            echo "  $0 --clean --rebuild # Reset completo"
            exit 0
            ;;
        *)
            log_error "Opção desconhecida: $1"
            echo "Use --help para ver as opções disponíveis"
            exit 1
            ;;
    esac
done

# Verificar dependências do sistema
log_info "Verificando dependências do sistema..."

# Verificar Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker não está instalado"
    log_info "Instale o Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Verificar Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose não está instalado"
    log_info "Instale o Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Verificar se Docker está rodando
if ! docker info &> /dev/null; then
    log_error "Docker não está rodando"
    log_info "Inicie o Docker e tente novamente"
    exit 1
fi

log_success "Dependências do sistema verificadas"

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
    docker-compose down -v --remove-orphans 2>/dev/null || true
    
    log_info "Removendo volumes..."
    docker volume prune -f 2>/dev/null || true
    
    log_info "Limpando cache Python..."
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    log_success "Limpeza concluída"
fi

# Rebuild se solicitado
if [ "$REBUILD_MODE" = true ]; then
    log_info "Rebuilding containers..."
    docker-compose build --no-cache
    log_success "Rebuild concluído"
fi

# Criar diretórios necessários
log_info "Criando estrutura de diretórios..."
mkdir -p uploads
mkdir -p volumes/minio
mkdir -p volumes/qdrant
mkdir -p volumes/n8n
mkdir -p static/css static/js static/images
mkdir -p src
mkdir -p templates

log_success "Diretórios criados"

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

# Flask
FLASK_ENV=production
FLASK_DEBUG=false

# Embedding
DEFAULT_EMBEDDING_MODEL=text-embedding-3-small
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

log_success "Arquivos do projeto verificados"

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
    docker-compose up -d qdrant minio n8n rag-demo-app
    log_info "Serviços iniciados em modo desenvolvimento (incluindo n8n)"
else
    docker-compose up -d
    log_info "Todos os serviços iniciados"
fi

# Aguardar inicialização
log_info "Aguardando serviços ficarem prontos..."
sleep 10

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

check_service "Qdrant" "http://localhost:6333/health"
check_service "MinIO" "http://localhost:9000/minio/health/live"
check_service "RAG-Demo App" "http://localhost:5000/api/test"

# Verificar n8n (em desenvolvimento e produção)
log_info "Verificando n8n (pode demorar mais)..."
sleep 5  # n8n demora mais para inicializar
if curl -f "http://localhost:5678" &> /dev/null; then
    log_success "n8n está rodando"
else
    log_warning "n8n ainda está inicializando (normal)"
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
echo "║  🔧 n8n:             http://localhost:5678                  ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}"
echo "🔑 Credenciais:"
echo "   • MinIO: minioadmin / minioadmin"
echo "   • n8n: admin / admin123"
echo -e "${NC}"

echo -e "${YELLOW}"
echo "📚 Próximos passos:"
echo "   1. Acesse http://localhost:5000"
echo "   2. Configure workflows no n8n (http://localhost:5678)"
echo "   3. Crie uma nova collection"
echo "   4. Faça upload de um documento"
echo "   5. Teste o gerador de Q&A"
echo "   6. Experimente o chat RAG"
echo -e "${NC}"

# Comandos úteis
echo -e "${BLUE}"
echo "🛠️  Comandos úteis:"
echo "   • Ver logs:           docker-compose logs -f"
echo "   • Parar serviços:     docker-compose down"
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

log_success "Setup concluído! Bom uso do RAG-Demo! 🚀" 