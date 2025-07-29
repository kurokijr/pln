#!/bin/bash

# RAG-Demo Clean Script
# Remove arquivos temporários e cache do projeto

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    RAG-Demo Cleaner                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar argumentos
DEEP_CLEAN=false
KEEP_VOLUMES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --deep)
            DEEP_CLEAN=true
            shift
            ;;
        --keep-volumes)
            KEEP_VOLUMES=true
            shift
            ;;
        --help)
            echo "Uso: $0 [OPÇÕES]"
            echo ""
            echo "OPÇÕES:"
            echo "  --deep          Limpeza profunda (remove volumes e images)"
            echo "  --keep-volumes  Manter volumes (não remove dados)"
            echo "  --help          Mostrar esta ajuda"
            echo ""
            echo "EXEMPLOS:"
            echo "  $0                    # Limpeza básica"
            echo "  $0 --deep            # Limpeza completa"
            echo "  $0 --keep-volumes    # Limpar sem perder dados"
            exit 0
            ;;
        *)
            log_warning "Opção desconhecida: $1"
            echo "Use --help para ver as opções disponíveis"
            exit 1
            ;;
    esac
done

# Limpeza básica
log_info "Iniciando limpeza básica..."

# Remover cache Python
log_info "Removendo cache Python..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true
log_success "Cache Python removido"

# Remover arquivos temporários
log_info "Removendo arquivos temporários..."
rm -f *.tmp *.temp 2>/dev/null || true
rm -f test_*.txt teste_*.txt debug_*.txt 2>/dev/null || true
rm -rf tmp/ temp/ 2>/dev/null || true
log_success "Arquivos temporários removidos"

# Remover logs
log_info "Removendo logs..."
rm -f *.log 2>/dev/null || true
rm -rf logs/ 2>/dev/null || true
log_success "Logs removidos"

# Parar containers
log_info "Parando containers Docker..."
docker-compose down 2>/dev/null || true
log_success "Containers parados"

# Limpeza profunda se solicitada
if [ "$DEEP_CLEAN" = true ]; then
    log_warning "Iniciando limpeza profunda..."
    
    if [ "$KEEP_VOLUMES" = false ]; then
        log_warning "Removendo volumes (dados serão perdidos)..."
        read -p "Tem certeza? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans 2>/dev/null || true
            docker volume prune -f 2>/dev/null || true
            log_success "Volumes removidos"
        else
            log_info "Mantendo volumes"
        fi
    else
        docker-compose down --remove-orphans 2>/dev/null || true
        log_success "Containers removidos (volumes mantidos)"
    fi
    
    # Remover imagens não utilizadas
    log_info "Removendo imagens Docker não utilizadas..."
    docker image prune -f 2>/dev/null || true
    log_success "Imagens limpas"
    
    # Remover redes não utilizadas
    log_info "Removendo redes Docker não utilizadas..."
    docker network prune -f 2>/dev/null || true
    log_success "Redes limpas"
fi

# Remover docker-compose override
log_info "Removendo configurações de desenvolvimento..."
rm -f docker-compose.override.yml 2>/dev/null || true
log_success "Configurações de desenvolvimento removidas"

# Limpar uploads vazios
if [ -d "uploads" ] && [ -z "$(ls -A uploads)" ]; then
    log_info "Diretório uploads vazio mantido"
else
    log_info "Verificando uploads..."
    ls -la uploads/ 2>/dev/null || true
fi

# Estatísticas finais
echo ""
log_info "Estatísticas do sistema:"

# Espaço em disco
if command -v df &> /dev/null; then
    echo "💾 Espaço disponível:"
    df -h . | tail -1 | awk '{print "   Usado: " $3 " | Disponível: " $4 " | Total: " $2}'
fi

# Docker
if command -v docker &> /dev/null; then
    echo "🐳 Docker:"
    echo "   Containers: $(docker ps -a --format '{{.Names}}' 2>/dev/null | wc -l || echo 0)"
    echo "   Imagens: $(docker images --format '{{.Repository}}' 2>/dev/null | wc -l || echo 0)"
    echo "   Volumes: $(docker volume ls --format '{{.Name}}' 2>/dev/null | wc -l || echo 0)"
fi

echo ""
log_success "Limpeza concluída! 🧹"

if [ "$DEEP_CLEAN" = true ]; then
    log_info "Para reiniciar o projeto:"
    echo "   ./setup.sh"
else
    log_info "Para reiniciar os serviços:"
    echo "   docker-compose up -d"
fi 