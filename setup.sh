#!/bin/bash

# RAG-Demo Setup Script
# Este script configura o ambiente RAG-Demo para desenvolvimento

set -e

echo "🚀 Configurando RAG-Demo..."

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "❌ Docker não está instalado. Por favor, instale o Docker primeiro."
    exit 1
fi

# Verificar se Docker Compose está instalado
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose não está instalado. Por favor, instale o Docker Compose primeiro."
    exit 1
fi

    # Criar diretórios necessários
    echo "📁 Criando diretórios..."
    mkdir -p uploads
    mkdir -p volumes/minio
    mkdir -p volumes/n8n
    mkdir -p volumes/qdrant

# Verificar se .env existe
if [ ! -f .env ]; then
    echo "📝 Criando arquivo .env..."
    cp env.example .env
    echo "⚠️  Por favor, edite o arquivo .env com suas configurações antes de continuar."
    echo "   Especialmente as chaves de API (OPENAI_API_KEY, GROK_API_KEY)"
    exit 1
fi

# Carregar variáveis de ambiente
source .env

# Verificar chaves de API
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY não está configurada no .env"
    echo "   Por favor, configure sua chave da OpenAI antes de continuar."
    exit 1
fi

echo "✅ Configuração básica concluída!"

# Perguntar se deve iniciar os serviços
read -p "🤔 Deseja iniciar os serviços agora? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🐳 Iniciando serviços Docker..."
    docker-compose up -d
    
    echo "⏳ Aguardando serviços ficarem prontos..."
    sleep 30
    
    echo "🔍 Verificando status dos serviços..."
    
    # Verificar Qdrant
    if curl -f http://localhost:6333/health &> /dev/null; then
        echo "✅ Qdrant está rodando"
    else
        echo "❌ Qdrant não está respondendo"
    fi
    
    # Verificar MinIO
    if curl -f http://localhost:9000/minio/health/live &> /dev/null; then
        echo "✅ MinIO está rodando"
    else
        echo "❌ MinIO não está respondendo"
    fi
    
    # Verificar aplicação Flask
    if curl -f http://localhost:5000 &> /dev/null; then
        echo "✅ Aplicação Flask está rodando"
    else
        echo "❌ Aplicação Flask não está respondendo"
    fi
    
    # Verificar n8n
    if curl -f http://localhost:5678 &> /dev/null; then
        echo "✅ n8n está rodando"
    else
        echo "❌ n8n não está respondendo"
    fi
    
    echo ""
    echo "🎉 RAG-Demo está pronto!"
    echo ""
    echo "📱 URLs de acesso:"
    echo "   • RAG-Demo: http://localhost:5000"
    echo "   • Qdrant Console: http://localhost:6333"
    echo "   • MinIO Console: http://localhost:9001"
    echo "   • n8n: http://localhost:5678"
    echo ""
    echo "🔑 Credenciais:"
    echo "   • MinIO: minioadmin / minioadmin"
    echo "   • n8n: admin / admin123"
    echo ""
    echo "📚 Próximos passos:"
    echo "   1. Acesse http://localhost:5000"
    echo "   2. Crie uma nova collection"
    echo "   3. Faça upload de um documento"
    echo "   4. Teste o chat RAG"
    echo ""
else
    echo "📋 Para iniciar os serviços manualmente, execute:"
    echo "   docker-compose up -d"
    echo ""
    echo "📚 Para mais informações, consulte o README.md"
fi

echo "✨ Setup concluído!" 