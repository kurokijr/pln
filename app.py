"""Aplicação Flask principal do RAG-Demo."""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from src.config import get_config
from src.document_processor import DocumentProcessor
from src.qa_generator import qa_generator
from langchain_core.documents import Document
from src.vector_store import QdrantVectorStore
from src.storage import StorageManager
from src.chat_service import ChatManager

# Configuração
config = get_config()

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(config)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar serviços
document_processor = DocumentProcessor()
storage_manager = StorageManager()
chat_manager = ChatManager()

# Verificar qual tipo de storage está sendo usado
print(f"🗄️ Tipo de storage: {'MinIO' if storage_manager.use_minio else 'Local'}", file=sys.stderr)
print(f"🗄️ Classe de storage: {type(storage_manager.storage).__name__}", file=sys.stderr)

# Inicializar banco de vetores (Qdrant)
import time
max_retries = 5
retry_delay = 5

for attempt in range(max_retries):
    try:
        print(f"🔄 Tentativa {attempt + 1}/{max_retries} de conectar ao Qdrant...")
        vector_store = QdrantVectorStore()
        use_qdrant = True
        print("✅ Conectado ao Qdrant com sucesso!")
        break
    except Exception as e:
        print(f"❌ Erro ao conectar ao Qdrant (tentativa {attempt + 1}): {e}")
        if attempt < max_retries - 1:
            print(f"⏳ Aguardando {retry_delay} segundos antes da próxima tentativa...")
            time.sleep(retry_delay)
        else:
            print("❌ Qdrant é obrigatório para este projeto")
            raise e

# Criar diretórios necessários
Path("uploads").mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)


def allowed_file(filename: str) -> bool:
    """Verifica se o arquivo é permitido."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')

@app.route('/api/test')
def test():
    """Endpoint de teste."""
    print("=== TESTE ENDPOINT ===", file=sys.stderr)
    return jsonify({'message': 'Teste OK'})


@app.route('/api/storage-info')
def storage_info():
    """Endpoint para informações do storage e documentos disponíveis."""
    print("=== TESTE STORAGE ENDPOINT ===", file=sys.stderr)
    try:
        storage_type = 'MinIO' if storage_manager.use_minio else 'Local'
        print(f"🗄️ Usando storage: {storage_type}", file=sys.stderr)
        
        # Listar documentos usando o método unificado
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents)}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'storage_type': storage_type,
            'storage_class': type(storage_manager.storage).__name__,
            'documents_count': len(documents),
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no storage: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['GET'])
def list_collections():
    """Lista collections disponíveis."""
    try:
        collections = vector_store.list_collections()
        
        return jsonify({
            'success': True,
            'collections': collections
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections', methods=['POST'])
def create_collection():
    """Cria uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        collection_name = data.get('name')
        embedding_model = data.get('embedding_model')
        description = data.get('description', '')
        
        if not collection_name or not embedding_model:
            return jsonify({'error': 'Nome da collection e modelo de embedding são obrigatórios'}), 400
        
        # Criar collection
        created_name = vector_store.create_collection(
            collection_name=collection_name,
            embedding_model=embedding_model,
            description=description
        )
        
        return jsonify({
            'success': True,
            'message': f'Collection "{created_name}" criada com sucesso',
            'collection_name': created_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>', methods=['DELETE'])
def delete_collection(collection_name: str):
    """Deleta uma collection."""
    try:
        success = vector_store.delete_collection(collection_name)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" deletada com sucesso'
            })
        else:
            return jsonify({'error': f'Collection "{collection_name}" não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/embedding-models', methods=['GET'])
def list_embedding_models():
    """Lista modelos de embedding disponíveis."""
    try:
        models = []
        for key, model_config in config.EMBEDDING_MODELS.items():
            models.append({
                'id': key,
                'name': model_config['name'],
                'model': model_config['model'],
                'dimension': model_config['dimension'],
                'provider': model_config['provider']
            })
        
        return jsonify({
            'success': True,
            'models': models
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/status', methods=['GET'])
def storage_status():
    """Verifica o status do sistema de armazenamento."""
    try:
        storage_type = "MinIO" if storage_manager.use_minio else "Local"
        storage_class = type(storage_manager.storage).__name__
        
        # Testar conectividade básica
        try:
            # Tentar listar documentos para testar se está funcionando
            files = storage_manager.get_document_list()
            connected = True
            error = None
        except Exception as e:
            connected = False
            error = str(e)
        
        return jsonify({
            'storage_type': storage_type,
            'storage_class': storage_class,
            'connected': connected,
            'error': error,
            'status': 'connected' if connected else 'disconnected'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files', methods=['GET'])
def list_storage_files():
    """Lista arquivos armazenados."""
    try:
        collection_name = request.args.get('collection')
        prefix = request.args.get('prefix', '')
        
        files = storage_manager.get_document_list(topic=collection_name)
        
        return jsonify({
            'success': True,
            'files': files,
            'total_files': len(files),
            'collection': collection_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/storage/files/<path:object_name>', methods=['DELETE'])
def delete_storage_file(object_name):
    """Deleta um arquivo do storage."""
    try:
        storage_manager.delete_document(object_name)
        return jsonify({
            'success': True,
            'message': f'Arquivo "{object_name}" deletado com sucesso'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload e processamento de documentos."""
    print("=== INÍCIO DO UPLOAD ===", file=sys.stderr)
    sys.stderr.flush()
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Nenhum arquivo enviado'}), 400
        
        file = request.files['file']
        collection_name = request.form.get('collection_name')
        
        if not file.filename:
            return jsonify({'error': 'Nome do arquivo não fornecido'}), 400
        
        if not collection_name:
            return jsonify({'error': 'Collection não selecionada'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de arquivo não permitido'}), 400
        
        # Salvar arquivo temporariamente
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        print(f"📁 Arquivo salvo temporariamente: {file_path}", file=sys.stderr)
        
        # === DEBUG: Verificar storage manager ===
        print(f"🔍 DEBUG Storage Manager:", file=sys.stderr)
        print(f"  - Tipo: {type(storage_manager.storage).__name__}", file=sys.stderr)
        print(f"  - Usando MinIO: {storage_manager.use_minio}", file=sys.stderr)
        
        # Upload do arquivo original para o MinIO
        try:
            print(f"🚀 Iniciando upload para MinIO na collection: {collection_name}", file=sys.stderr)
            print(f"📂 Arquivo: {file_path}", file=sys.stderr)
            sys.stderr.flush()
            
            upload_result = storage_manager.upload_document(file_path, topic=collection_name)
            
            print(f"✅ Upload para MinIO concluído:", file=sys.stderr)
            print(f"   - Path: {upload_result['original_path']}", file=sys.stderr)
            print(f"   - Object: {upload_result['object_name']}", file=sys.stderr)
            print(f"   - Topic: {upload_result['topic']}", file=sys.stderr)
            sys.stderr.flush()
            
        except Exception as e:
            print(f"❌ ERRO CRÍTICO no upload para MinIO: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': f'Erro ao fazer upload para MinIO: {str(e)}'}), 500
        
        # Processar documento
        print(f"🔍 Iniciando processamento do arquivo: {file_path}", file=sys.stderr)
        try:
            result = document_processor.process_document(file_path)
            print(f"✅ Processamento concluído: {result.keys() if result else 'None'}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Erro no processamento: {str(e)}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': str(e)}), 500
        
        if not result or 'chunks' not in result:
            print(f"❌ Resultado inválido: {result}", file=sys.stderr)
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            return jsonify({'error': 'Não foi possível processar o documento'}), 400
        
        # Salvar documento processado no MinIO
        try:
            print(f"💾 Salvando documento processado no MinIO", file=sys.stderr)
            processed_filename = f"processed_{filename}"
            processed_path = storage_manager.save_processed_document(
                text=result['enhanced_text'],
                file_name=processed_filename,
                topic=collection_name
            )
            print(f"✅ Documento processado salvo: {processed_path}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Aviso: Erro ao salvar documento processado no MinIO: {str(e)}", file=sys.stderr)
            # Continuar mesmo se falhar ao salvar o processado
            processed_path = None
        
        # Atualizar metadados dos chunks com informações do MinIO
        print(f"📝 Atualizando metadados dos chunks", file=sys.stderr)
        for i, chunk in enumerate(result['chunks']):
            chunk.metadata.update({
                'collection_name': collection_name,
                'minio_original_path': upload_result['original_path'],
                'minio_processed_path': processed_path,
                'upload_timestamp': upload_result['upload_time']
            })
            print(f"   Chunk {i+1}: {len(chunk.page_content)} chars, metadata atualizado", file=sys.stderr)
        
        # Inserir no banco de vetores
        print(f"🔗 Inserindo no banco de vetores (QDrant)", file=sys.stderr)
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=result['chunks']
        )
        
        if success:
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
                print(f"🗑️ Arquivo temporário removido: {file_path}", file=sys.stderr)
            except:
                pass
            
            print(f"🎉 UPLOAD COMPLETO COM SUCESSO!", file=sys.stderr)
            print(f"   - MinIO: {upload_result['original_path']}", file=sys.stderr)
            print(f"   - QDrant: {len(result['chunks'])} chunks", file=sys.stderr)
            sys.stderr.flush()
            
            return jsonify({
                'success': True,
                'message': f'Documento "{filename}" processado e inserido com sucesso',
                'file_name': filename,
                'chunks_count': len(result['chunks']),
                'minio_path': upload_result['original_path'],
                'collection_name': collection_name
            })
        else:
            return jsonify({'error': 'Erro ao inserir documentos no banco de vetores'}), 500
            
    except Exception as e:
        print(f"❌ ERRO GERAL NO UPLOAD: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        # Limpar arquivo temporário em caso de erro
        try:
            if 'file_path' in locals():
                os.remove(file_path)
        except:
            pass
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para chat com RAG."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        message = data.get('message')
        collection_name = data.get('collection_name')
        session_id = data.get('session_id')
        
        if not message or not collection_name:
            return jsonify({'error': 'Mensagem e collection são obrigatórios'}), 400
        
        # Buscar documentos similares
        similar_docs = vector_store.search_similar(
            collection_name=collection_name,
            query=message,
            top_k=5
        )
        
        if not similar_docs:
            return jsonify({
                'success': True,
                'response': 'Desculpe, não encontrei informações relevantes para responder sua pergunta.',
                'sources': []
            })
        
        # Gerar resposta usando o chat manager
        response = chat_manager.generate_response(
            message=message,
            context_docs=similar_docs,
            session_id=session_id
        )
        
        return jsonify({
            'success': True,
            'response': response,
            'sources': similar_docs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """Lista sessões de chat."""
    try:
        sessions = chat_manager.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """Cria uma nova sessão de chat."""
    try:
        data = request.get_json()
        session_name = data.get('name', 'Nova Sessão')
        
        session_id = chat_manager.create_session(session_name)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session_name': session_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Deleta uma sessão de chat."""
    try:
        success = chat_manager.delete_session(session_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Sessão deletada com sucesso'
            })
        else:
            return jsonify({'error': 'Sessão não encontrada'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """Lista documentos disponíveis no MinIO."""
    print("=== ENDPOINT /api/documents CHAMADO ===", file=sys.stderr)
    try:
        print("🔍 Chamando storage_manager.get_document_list()", file=sys.stderr)
        documents = storage_manager.get_document_list()
        print(f"✅ Documentos encontrados: {len(documents) if documents else 0}", file=sys.stderr)
        
        return jsonify({
            'success': True,
            'documents': documents or []
        })
    except Exception as e:
        print(f"❌ Erro no endpoint /api/documents: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/documents', methods=['GET'])
def list_collection_documents(collection_name: str):
    """Lista documentos de uma collection."""
    try:
        limit = request.args.get('limit', 1000, type=int)
        
        documents = vector_store.list_collection_documents(
            collection_name=collection_name,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'documents': documents,
            'total': len(documents)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/recalculate-count', methods=['POST'])
def recalculate_collection_count(collection_name: str):
    """Recalcula a contagem de documentos de uma collection."""
    try:
        vector_store._recalculate_collection_document_count(collection_name)
        return jsonify({
            'success': True,
            'message': f'Contagem de documentos da collection "{collection_name}" recalculada'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<document_name>/content', methods=['GET'])
def get_document_content(document_name: str):
    """Obtém o conteúdo de um documento específico."""
    try:
        # Decodificar o nome do documento se necessário
        import urllib.parse
        document_name = urllib.parse.unquote(document_name)
        
        # Buscar o documento no MinIO
        try:
            content_bytes = storage_manager.storage.download_file(document_name)
            content = content_bytes.decode('utf-8')
        except Exception as e:
            return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        
        return jsonify({
            'success': True,
            'content': content,
            'document_name': document_name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/collections/<collection_name>/content', methods=['GET'])
def get_collection_content(collection_name: str):
    """Obtém o conteúdo de todos os documentos de uma collection para geração de Q&A."""
    try:
        # Verificar se é uma requisição para documento específico
        document_name = request.args.get('document')
        
        if document_name:
            # Buscar documento específico no storage
            try:
                if storage_manager.use_minio:
                    # MinIO storage
                    content_bytes = storage_manager.storage.download_file(document_name)
                    content = content_bytes.decode('utf-8')
                else:
                    # Local storage
                    content = storage_manager.storage.read_file(document_name)
                
                return jsonify({
                    'success': True,
                    'content': content,
                    'document_name': document_name,
                    'document_count': 1
                })
            except Exception as e:
                return jsonify({'error': f'Documento não encontrado: {str(e)}'}), 404
        else:
            # Comportamento original - conteúdo da collection
            documents = vector_store.list_collection_documents(collection_name)
            
            # Concatenar conteúdo de todos os documentos
            content = ""
            for doc in documents:
                if doc.get('content'):
                    content += doc['content'] + "\n\n"
            
            return jsonify({
                'success': True,
                'content': content,
                'document_count': len(documents)
            })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/qa-generate', methods=['POST'])
def generate_qa():
    """Gera perguntas e respostas a partir de um documento."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        content = data.get('content')
        collection_name = data.get('collection_name')
        num_questions = data.get('num_questions', 10)
        difficulty = data.get('difficulty', 'Intermediário')
        temperature = data.get('temperature', 0.5)
        context_keywords = data.get('context_keywords', '')
        custom_prompt = data.get('custom_prompt', '')
        
        if not content or not collection_name:
            return jsonify({'error': 'Conteúdo e collection são obrigatórios'}), 400
        
        # Parâmetros para geração de Q&A
        params = {
            'num_questions': num_questions,
            'context_keywords': context_keywords,
            'difficulty': difficulty,
            'temperature': temperature,
            'custom_prompt': custom_prompt
        }
        
        # Gerar Q&A
        qa_content = qa_generator.generate_qa_pairs(content, params)
        
        if not qa_content:
            return jsonify({'error': 'Não foi possível gerar perguntas e respostas'}), 400
        
        # Converter para documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        # Inserir no banco de vetores
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{len(documents)} pares de Q&A gerados e inseridos com sucesso',
                'qa_content': qa_content,
                'qa_count': len(documents)
            })
        else:
            return jsonify({'error': 'Erro ao inserir Q&A no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/create-qa-embeddings', methods=['POST'])
def create_qa_embeddings():
    """Cria embeddings a partir dos Q&As gerados e insere em uma nova collection."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        qa_content = data.get('qa_content')
        collection_name = data.get('collection_name')
        embedding_model = data.get('embedding_model', 'text-embedding-3-small')
        
        if not qa_content or not collection_name:
            return jsonify({'error': 'Conteúdo Q&A e nome da collection são obrigatórios'}), 400
        
        # Converter Q&A em documentos
        documents = qa_generator.qa_to_documents(qa_content, collection_name)
        
        if not documents:
            return jsonify({'error': 'Não foi possível processar os Q&As'}), 400
        
        # Inserir documentos na nova collection
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Collection "{collection_name}" criada com {len(documents)} Q&As como embeddings',
                'collection_name': collection_name,
                'documents_count': len(documents),
                'embedding_model': embedding_model
            })
        else:
            return jsonify({'error': 'Erro ao criar embeddings no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=== ROTAS REGISTRADAS ===", file=sys.stderr)
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}", file=sys.stderr)
    print("=========================", file=sys.stderr)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) 