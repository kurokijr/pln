"""Gerenciamento de armazenamento com MinIO."""

import os
import json
from typing import List, Dict, Any, Optional, BinaryIO
from pathlib import Path
from datetime import datetime

from minio import Minio
from minio.error import S3Error

from src.config import get_config

config = get_config()


class MinIOStorage:
    """Interface para armazenamento MinIO."""
    
    def __init__(self):
        """Inicializa a conexão com MinIO."""
        self.client = Minio(
            endpoint=config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=False  # HTTP para desenvolvimento local
        )
        self.bucket_name = config.MINIO_BUCKET_DOCUMENTS
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Garante que o bucket existe."""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"Erro ao criar bucket: {str(e)}")
    
    def upload_file(self, file_path: str, object_name: str, topic: str = "default") -> str:
        """Faz upload de um arquivo para o MinIO."""
        try:
            # Estrutura: topic/originals/filename
            object_path = f"{topic}/originals/{object_name}"
            
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                file_path=file_path
            )
            
            return object_path
            
        except S3Error as e:
            raise Exception(f"Erro no upload: {str(e)}")
    
    def upload_text(self, text: str, object_name: str, topic: str = "default") -> str:
        """Faz upload de texto como arquivo para o MinIO."""
        try:
            # Estrutura: topic/converted/filename.md
            object_path = f"{topic}/converted/{object_name}.md"
            
            # Salvar texto temporariamente
            temp_path = f"/tmp/{object_name}.md"
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                file_path=temp_path
            )
            
            # Limpar arquivo temporário
            os.remove(temp_path)
            
            return object_path
            
        except Exception as e:
            raise Exception(f"Erro no upload de texto: {str(e)}")
    
    def download_file(self, object_name: str) -> bytes:
        """Download de um arquivo do MinIO."""
        try:
            response = self.client.get_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            return response.read()
            
        except S3Error as e:
            raise Exception(f"Erro no download: {str(e)}")
    
    def list_files(self, topic: str = None, prefix: str = "") -> List[Dict[str, Any]]:
        """Lista arquivos no bucket."""
        try:
            objects = []
            
            if topic:
                prefix = f"{topic}/{prefix}"
            
            for obj in self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            ):
                objects.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag
                })
            
            return objects
            
        except S3Error as e:
            raise Exception(f"Erro ao listar arquivos: {str(e)}")
    
    def delete_file(self, object_name: str):
        """Deleta um arquivo do MinIO."""
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
        except S3Error as e:
            raise Exception(f"Erro ao deletar arquivo: {str(e)}")
    
    def get_file_url(self, object_name: str, expires: int = 3600) -> str:
        """Gera URL temporária para download."""
        try:
            return self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                expires=expires
            )
        except S3Error as e:
            raise Exception(f"Erro ao gerar URL: {str(e)}")


class LocalStorage:
    """Armazenamento local como fallback."""
    
    def __init__(self, base_path: str = "data/storage"):
        """Inicializa o armazenamento local."""
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file_path: str, object_name: str, topic: str = "default") -> str:
        """Salva um arquivo localmente."""
        try:
            # Criar estrutura de diretórios
            topic_path = self.base_path / topic / "originals"
            topic_path.mkdir(parents=True, exist_ok=True)
            
            # Copiar arquivo
            dest_path = topic_path / object_name
            import shutil
            shutil.copy2(file_path, dest_path)
            
            return str(dest_path)
            
        except Exception as e:
            raise Exception(f"Erro ao salvar arquivo: {str(e)}")
    
    def save_text(self, text: str, object_name: str, topic: str = "default") -> str:
        """Salva texto como arquivo localmente."""
        try:
            # Criar estrutura de diretórios
            topic_path = self.base_path / topic / "converted"
            topic_path.mkdir(parents=True, exist_ok=True)
            
            # Salvar arquivo
            file_path = topic_path / f"{object_name}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            return str(file_path)
            
        except Exception as e:
            raise Exception(f"Erro ao salvar texto: {str(e)}")
    
    def read_file(self, file_path: str) -> str:
        """Lê um arquivo local."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"Erro ao ler arquivo: {str(e)}")
    
    def list_files(self, topic: str = None) -> List[Dict[str, Any]]:
        """Lista arquivos locais."""
        try:
            files = []
            base = self.base_path / topic if topic else self.base_path
            
            if not base.exists():
                return files
            
            for file_path in base.rglob("*"):
                if file_path.is_file():
                    stat = file_path.stat()
                    files.append({
                        "name": str(file_path.relative_to(self.base_path)),
                        "size": stat.st_size,
                        "last_modified": datetime.fromtimestamp(stat.st_mtime),
                        "path": str(file_path)
                    })
            
            return files
            
        except Exception as e:
            raise Exception(f"Erro ao listar arquivos: {str(e)}")
    
    def delete_file(self, file_path: str):
        """Deleta um arquivo local."""
        try:
            Path(file_path).unlink()
        except Exception as e:
            raise Exception(f"Erro ao deletar arquivo: {str(e)}")


class StorageManager:
    """Gerenciador de armazenamento com fallback."""
    
    def __init__(self, use_minio: bool = True):
        """Inicializa o gerenciador de armazenamento."""
        self.use_minio = use_minio
        
        if use_minio:
            try:
                self.storage = MinIOStorage()
            except Exception as e:
                print(f"MinIO não disponível, usando armazenamento local: {e}")
                self.storage = LocalStorage()
                self.use_minio = False
        else:
            self.storage = LocalStorage()
    
    def upload_document(self, file_path: str, topic: str = "default") -> Dict[str, str]:
        """Upload de documento com metadados."""
        try:
            file_name = Path(file_path).name
            object_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
            
            # Upload do arquivo original
            original_path = self.storage.upload_file(file_path, object_name, topic)
            
            return {
                "original_path": original_path,
                "file_name": file_name,
                "object_name": object_name,
                "topic": topic,
                "upload_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Erro no upload de documento: {str(e)}")
    
    def save_processed_document(self, text: str, file_name: str, topic: str = "default") -> str:
        """Salva documento processado."""
        try:
            object_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
            return self.storage.upload_text(text, object_name, topic)
            
        except Exception as e:
            raise Exception(f"Erro ao salvar documento processado: {str(e)}")
    
    def get_document_list(self, topic: str = None) -> List[Dict[str, Any]]:
        """Lista documentos armazenados."""
        try:
            return self.storage.list_files(topic)
        except Exception as e:
            raise Exception(f"Erro ao listar documentos: {str(e)}")
    
    def delete_document(self, object_name: str):
        """Deleta um documento."""
        try:
            self.storage.delete_file(object_name)
        except Exception as e:
            raise Exception(f"Erro ao deletar documento: {str(e)}") 