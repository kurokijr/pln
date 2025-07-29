# Configuração do Bucket MinIO - RAG-Demo

## 📦 Bucket Padrão

O RAG-Demo usa o bucket **`documents`** como padrão para armazenamento de arquivos.

### 🔧 Configuração

#### Variável de Ambiente
```env
MINIO_BUCKET_NAME=documents
```

#### Código Python
```python
# src/config.py
MINIO_BUCKET_DOCUMENTS = os.getenv("MINIO_BUCKET_NAME", "documents")
```

## 🗂️ Estrutura do Bucket

O bucket `documents` organiza arquivos por collection:

```
documents/
├── collection1/
│   ├── originals/
│   │   ├── 20250129_120000_document1.pdf
│   │   └── 20250129_120001_document2.docx
│   └── converted/
│       ├── 20250129_120000_processed_document1.pdf.md
│       └── 20250129_120001_processed_document2.docx.md
├── collection2/
│   ├── originals/
│   └── converted/
└── temp/
    └── upload_temp_files
```

## 🛠️ Operações

### Criar Bucket (Automático)
O RAG-Demo cria automaticamente o bucket na inicialização:

```python
def _ensure_bucket_exists(self):
    if not self.client.bucket_exists(self.bucket_name):
        self.client.make_bucket(self.bucket_name)
```

### Verificar Existência
```bash
# Via MinIO Console
curl http://localhost:9000/minio/health/live

# Via API
curl http://localhost:5000/api/storage-info
```

## 🔍 Monitoramento

### MinIO Console
- **URL**: http://localhost:9001
- **Login**: minioadmin / minioadmin
- **Bucket**: `documents`

### Estatísticas Atuais
Conforme mostrado no MinIO Console:
- **Objetos**: 8
- **Tamanho**: 62.2 KiB
- **Acesso**: R/W (Read/Write)

## ⚙️ Configurações Alternativas

### Bucket Personalizado
```env
MINIO_BUCKET_NAME=meu-bucket-customizado
```

### Múltiplos Buckets (Futuro)
Para implementar múltiplos buckets:

```python
# Configuração por ambiente
BUCKETS = {
    'documents': 'documents',
    'images': 'rag-images', 
    'backups': 'rag-backups'
}
```

## 🚨 Importante

1. **Nome Padrão**: Use sempre `documents` para compatibilidade
2. **Criação Automática**: O bucket é criado automaticamente se não existir
3. **Permissões**: R/W por padrão para desenvolvimento
4. **Backup**: Considere backup regular do bucket em produção

## 🔄 Migração

Se precisar migrar de `rag-documents` para `documents`:

```bash
# 1. Parar aplicação
docker-compose down

# 2. Atualizar .env
echo "MINIO_BUCKET_NAME=documents" >> .env

# 3. Reiniciar
docker-compose up -d

# 4. Verificar no console MinIO
open http://localhost:9001
```

---

**Bucket `documents`** - Padrão oficial do RAG-Demo! 📦 