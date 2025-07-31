# 🔍 Estratégia de Debug - Busca Semântica por Modelo

## 📋 Estratégia Completa de Debug

### 1. **Verificação das Collections**

**Passo 1: Clique no botão "Debug"** na interface da Busca Semântica
- Isso executará o endpoint `/api/debug/collections-by-model`
- Mostrará todas as collections e seus modelos associados

### 2. **Debug via Console do Navegador**

Cole no console do navegador (F12 → Console):

```javascript
// 1. Verificar collections por modelo
async function debugCollections() {
    try {
        const response = await fetch('/api/debug/collections-by-model');
        const data = await response.json();
        console.log('🔍 DEBUG COLLECTIONS:', data);
        return data;
    } catch (error) {
        console.error('❌ Erro:', error);
    }
}

// 2. Testar busca semântica
async function testSemanticSearch(query = "Qual é a localização do Condomínio Cláudio COhen?", model = "openai") {
    try {
        const response = await fetch('/api/semantic-search-by-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, model })
        });
        const data = await response.json();
        console.log('🚀 SEMANTIC SEARCH:', data);
        return data;
    } catch (error) {
        console.error('❌ Erro na busca:', error);
    }
}

// 3. Verificar modelos disponíveis
async function checkModels() {
    try {
        const response = await fetch('/api/embedding-models');
        const data = await response.json();
        console.log('📊 MODELOS:', data);
        return data;
    } catch (error) {
        console.error('❌ Erro nos modelos:', error);
    }
}

// Executar todos os debugs
async function runFullDebug() {
    console.log('🔥 INICIANDO DEBUG COMPLETO...');
    
    console.log('\n1️⃣ Verificando modelos...');
    await checkModels();
    
    console.log('\n2️⃣ Verificando collections...');
    const collections = await debugCollections();
    
    console.log('\n3️⃣ Testando busca semântica...');
    await testSemanticSearch();
    
    console.log('\n✅ DEBUG COMPLETO!');
}

// Execute: runFullDebug()
```

### 3. **Verificação no Backend (Logs)**

**Logs que você deve ver no terminal do Docker:**

```bash
# 1. Logs de collections
🔍 DEBUG: Buscando collections para modelo 'openai'
🔍 DEBUG: Total de collections encontradas: X
🔍 DEBUG: Collection 1: nome_da_collection
   - exists_in_qdrant: true/false
   - embedding_model: openai/gemini
   - provider: openai/gemini

# 2. Logs de busca
🚀 DEBUG: Iniciando busca semântica
   - query: 'sua pergunta'
   - model_id: 'openai'
   - top_k: 5
   - similarity_threshold: 0.1
```

### 4. **Possíveis Problemas e Soluções**

#### ❌ **Erro: "Nenhuma collection encontrada para o modelo openai"**

**Possíveis causas:**
1. Collections não foram criadas com modelo OpenAI
2. Metadados das collections estão inconsistentes
3. Campo `embedding_model` ou `provider` não está sendo salvo corretamente

**Verificação:**
```javascript
// No console do navegador
debugCollections().then(data => {
    console.log('Collections por modelo:', data.debug_info.collections_by_model);
    console.log('Detalhes das collections:', data.debug_info.collections);
});
```

#### ✅ **Solução 1: Recriar Collection com Modelo Correto**
1. Vá para Collections → Nova Collection
2. Selecione explicitamente "OpenAI Text Embedding"
3. Faça upload de alguns documentos

#### ✅ **Solução 2: Verificar se Collections Existem no Qdrant**
- Verifique se `exists_in_qdrant: true` nas collections
- Se `false`, a collection não foi sincronizada

### 5. **Testes Graduais**

#### **Teste 1: Verificar se API responde**
```bash
curl http://localhost:5000/api/embedding-models
```

#### **Teste 2: Debug das collections**
```bash
curl http://localhost:5000/api/debug/collections-by-model
```

#### **Teste 3: Busca semântica**
```bash
curl -X POST http://localhost:5000/api/semantic-search-by-model \
  -H "Content-Type: application/json" \
  -d '{"query": "teste", "model": "openai"}'
```

### 6. **Checklist de Verificação**

- [ ] Collections existem e têm `exists_in_qdrant: true`
- [ ] Collections têm `embedding_model` ou `provider` corretos
- [ ] Modelo selecionado existe em `EMBEDDING_MODELS`
- [ ] Collections têm documentos (`document_count > 0`)
- [ ] APIs OpenAI/Gemini estão configuradas (`.env`)

### 7. **Informações Detalhadas dos Chunks**

Na interface melhorada, os chunks são exibidos com:

```
📄 Chunks Utilizados (X)
├── 📂 Collection - Chunk 1     [85.5% similaridade]
├── 📄 Documento: arquivo.pdf
└── Conteúdo do chunk...
```

**Campos exibidos:**
- ✅ Collection de origem
- ✅ Percentual de similaridade (com destaque visual)
- ✅ Nome do documento
- ✅ Conteúdo completo do chunk
- ✅ Collections consultadas
- ✅ Total de chunks encontrados

### 8. **Debug Avançado - Se Nada Funcionar**

1. **Verificar se Qdrant está rodando:**
```bash
curl http://localhost:6333/health
```

2. **Verificar logs do Docker:**
```bash
docker-compose logs app
docker-compose logs qdrant
```

3. **Verificar se collections existem no Qdrant:**
```bash
curl http://localhost:6333/collections
```

### 9. **Scripts de Recuperação**

Se as collections estiverem com metadados incorretos, você pode:

1. **Recriar a collection** com o modelo correto
2. **Fazer upload dos documentos novamente**
3. **Verificar se o modelo selecionado na criação é o correto**

---

## 🎯 Resumo da Estratégia

1. ✅ **Interface de Debug** implementada (botão "Debug")
2. ✅ **Logs detalhados** no backend
3. ✅ **Endpoint de debug** (`/api/debug/collections-by-model`)
4. ✅ **Exibição melhorada** dos chunks com percentuais
5. ✅ **Scripts de console** para teste manual
6. ✅ **Checklist completo** de verificação

Execute os passos na ordem e você identificará exatamente onde está o problema! 🚀