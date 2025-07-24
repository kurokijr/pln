"""Aplicação Flask principal do RAG-Demo."""

import os
import json
from pathlib import Path
from typing import Dict, Any

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

from src.config import get_config
from src.document_processor import DocumentProcessor, QAGenerator
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
qa_generator = QAGenerator()
storage_manager = StorageManager()
chat_manager = ChatManager()

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


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload e processamento de documentos."""
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
        
        # Salvar arquivo
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Processar documento
        documents = document_processor.process_document(file_path)
        
        if not documents:
            return jsonify({'error': 'Não foi possível processar o documento'}), 400
        
        # Inserir no banco de vetores
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            # Limpar arquivo temporário
            try:
                os.remove(file_path)
            except:
                pass
            
            return jsonify({
                'success': True,
                'message': f'Documento "{filename}" processado e inserido com sucesso',
                'file_name': filename,
                'chunks_count': len(documents)
            })
        else:
            return jsonify({'error': 'Erro ao inserir documentos no banco de vetores'}), 500
            
    except Exception as e:
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


@app.route('/api/qa-generate', methods=['POST'])
def generate_qa():
    """Gera perguntas e respostas a partir de um documento."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Dados não fornecidos'}), 400
        
        content = data.get('content')
        collection_name = data.get('collection_name')
        
        if not content or not collection_name:
            return jsonify({'error': 'Conteúdo e collection são obrigatórios'}), 400
        
        # Gerar Q&A
        qa_pairs = qa_generator.generate_qa_pairs(content)
        
        if not qa_pairs:
            return jsonify({'error': 'Não foi possível gerar perguntas e respostas'}), 400
        
        # Converter para documentos
        documents = []
        for i, (question, answer) in enumerate(qa_pairs):
            doc = Document(
                page_content=f"Pergunta: {question}\nResposta: {answer}",
                metadata={
                    'type': 'qa_pair',
                    'question': question,
                    'answer': answer,
                    'index': i,
                    'collection': collection_name
                }
            )
            documents.append(doc)
        
        # Inserir no banco de vetores
        success = vector_store.insert_documents(
            collection_name=collection_name,
            documents=documents
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'{len(qa_pairs)} pares de Q&A gerados e inseridos com sucesso',
                'qa_pairs': qa_pairs
            })
        else:
            return jsonify({'error': 'Erro ao inserir Q&A no banco de vetores'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True) 