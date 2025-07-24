#!/usr/bin/env python3
"""Teste para verificar se a API do Gemini está sendo chamada corretamente."""

import os
import sys
sys.path.append('src')

from src.config import get_config
from src.vector_store import EmbeddingManager

def test_gemini_embedding():
    """Testa se a API do Gemini está funcionando corretamente."""
    config = get_config()
    
    print("🔍 Testando configuração do Gemini...")
    print(f"GEMINI_API_KEY configurada: {'Sim' if config.GEMINI_API_KEY else 'Não'}")
    print(f"Modelo Gemini configurado: {config.EMBEDDING_MODELS['gemini']}")
    
    if not config.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY não configurada!")
        return False
    
    try:
        print("\n🚀 Inicializando EmbeddingManager com modelo Gemini...")
        embedding_manager = EmbeddingManager("gemini")
        
        print("✅ EmbeddingManager inicializado com sucesso!")
        print(f"Modelo: {embedding_manager.model_name}")
        print(f"Provider: {embedding_manager.provider}")
        print(f"Dimensão: {embedding_manager.dimension}")
        
        # Teste com um texto simples
        test_text = "Este é um teste para verificar se a API do Gemini está funcionando."
        print(f"\n📝 Testando embedding com texto: '{test_text}'")
        
        embedding = embedding_manager.get_embedding(test_text)
        
        print(f"✅ Embedding gerado com sucesso!")
        print(f"Dimensão do embedding: {len(embedding)}")
        print(f"Primeiros 5 valores: {embedding[:5]}")
        
        # Teste com múltiplos textos
        test_texts = [
            "Primeiro texto para teste.",
            "Segundo texto para teste.",
            "Terceiro texto para teste."
        ]
        
        print(f"\n📝 Testando embeddings múltiplos com {len(test_texts)} textos...")
        embeddings = embedding_manager.get_embeddings(test_texts)
        
        print(f"✅ {len(embeddings)} embeddings gerados com sucesso!")
        for i, emb in enumerate(embeddings):
            print(f"  Texto {i+1}: {len(emb)} dimensões")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar Gemini: {e}")
        return False

def test_openai_embedding():
    """Testa se a API do OpenAI está funcionando corretamente."""
    config = get_config()
    
    print("\n🔍 Testando configuração do OpenAI...")
    print(f"OPENAI_API_KEY configurada: {'Sim' if config.OPENAI_API_KEY else 'Não'}")
    print(f"Modelo OpenAI configurado: {config.EMBEDDING_MODELS['openai']}")
    
    if not config.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY não configurada!")
        return False
    
    try:
        print("\n🚀 Inicializando EmbeddingManager com modelo OpenAI...")
        embedding_manager = EmbeddingManager("openai")
        
        print("✅ EmbeddingManager inicializado com sucesso!")
        print(f"Modelo: {embedding_manager.model_name}")
        print(f"Provider: {embedding_manager.provider}")
        print(f"Dimensão: {embedding_manager.dimension}")
        
        # Teste com um texto simples
        test_text = "Este é um teste para verificar se a API do OpenAI está funcionando."
        print(f"\n📝 Testando embedding com texto: '{test_text}'")
        
        embedding = embedding_manager.get_embedding(test_text)
        
        print(f"✅ Embedding gerado com sucesso!")
        print(f"Dimensão do embedding: {len(embedding)}")
        print(f"Primeiros 5 valores: {embedding[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao testar OpenAI: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Iniciando testes de embedding...\n")
    
    # Testar Gemini
    gemini_success = test_gemini_embedding()
    
    # Testar OpenAI
    openai_success = test_openai_embedding()
    
    print("\n" + "="*50)
    print("📊 RESUMO DOS TESTES:")
    print(f"Gemini: {'✅ PASSOU' if gemini_success else '❌ FALHOU'}")
    print(f"OpenAI: {'✅ PASSOU' if openai_success else '❌ FALHOU'}")
    
    if gemini_success and openai_success:
        print("\n🎉 Todos os testes passaram! As APIs estão funcionando corretamente.")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique as configurações das APIs.") 