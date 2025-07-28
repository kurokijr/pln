"""
Gerador de Perguntas e Respostas (Q&A)
Baseado no exemplo qa_page.py, adaptado para arquitetura Flask + Qdrant
"""

import re
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import os

# Configurações
INITIAL_CHUNK_SIZE = 15000
MAX_WORKERS = 4
MAX_RETRIES = 3
REQUEST_TIMEOUT = 60

class QAGenerator:
    """Gerador de perguntas e respostas baseado em documentos."""
    
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.model_qa_generator = os.getenv("MODEL_QA_GENERATOR", "gpt-4o-mini")
        
    def dynamic_chunk_size(self, text_length: int) -> int:
        """Determina o tamanho do chunk baseado no tamanho do texto."""
        if text_length > 200000:
            return 30000
        elif text_length > 100000:
            return 20000
        return INITIAL_CHUNK_SIZE
    
    def chunk_document(self, text: str) -> List[str]:
        """Divide o documento em chunks para processamento."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.dynamic_chunk_size(len(text)),
            chunk_overlap=int(self.dynamic_chunk_size(len(text)) * 0.1),
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        )
        return splitter.split_text(text)
    
    def process_chunk(self, args: tuple) -> tuple[str, Optional[str]]:
        """Processa um chunk individual para gerar Q&A."""
        chunk, prompt_template, params = args
        
        try:
            llm = ChatOpenAI(
                api_key=self.openai_api_key,
                temperature=params['temperature'],
                model=self.model_qa_generator,
                max_retries=2,
                timeout=REQUEST_TIMEOUT
            )
            prompt = ChatPromptTemplate.from_template(prompt_template)
            chain = prompt | llm

            questions_needed = params['questions_per_chunk']
            result = ""

            for attempt in range(MAX_RETRIES):
                try:
                    response = chain.invoke({
                        "num_questions": questions_needed,
                        "context_keywords": params['context_keywords'],
                        "difficulty": params['difficulty'],
                        "document_text": chunk
                    }).content

                    generated = len(re.findall(r"\*\*Pergunta \d+:", response))
                    result += response + "\n\n"

                    if generated >= questions_needed:
                        break

                    questions_needed -= generated

                except Exception as e:
                    if "timed out" in str(e).lower() and attempt < MAX_RETRIES - 1:
                        time.sleep(2)  # Espera antes de retentar
                        continue
                    else:
                        raise e

            return result, None

        except Exception as e:
            return None, str(e)
    
    def generate_qa_pairs(self, doc_text: str, params: Dict[str, Any]) -> str:
        """Gera pares de perguntas e respostas a partir do texto do documento."""
        chunks = self.chunk_document(doc_text)
        total_chunks = len(chunks)

        if total_chunks == 0:
            return ""

        params['questions_per_chunk'] = max(2, params['num_questions'] // max(total_chunks, 1))

        # Prompt padrão para geração de Q&A
        default_prompt = """Você é um especialista em criação de conteúdos educacionais. 
        Gere no mínimo {num_questions} perguntas e respostas baseadas no documento abaixo:

        REGRAS:
        1. Foco nos contextos: {context_keywords} (priorizar estes termos)
        2. Formato obrigatório: 
        **Pergunta {{número}}:** [texto] \\n\\n **Resposta {{número}}:** [texto]
        3. Nível de detalhe: adequado para profissionais de nível {difficulty}
        4. Inclua exemplos quando relevante

        DOCUMENTO:
        {document_text}"""
        
        # Usar prompt personalizado se fornecido
        prompt_template = params.get('custom_prompt', default_prompt)

        qa_buffer = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(self.process_chunk, (chunk, prompt_template, params)): i
                       for i, chunk in enumerate(chunks)}

            for future in as_completed(futures):
                chunk_index = futures[future]
                result, error = future.result()

                if result:
                    qa_buffer.append(result)
                elif error:
                    print(f"Erro no chunk {chunk_index + 1}: {error}")

        full_content = self.clean_qa_content("\n\n".join(qa_buffer), params['num_questions'])

        # Verificar se precisamos gerar QAs adicionais
        final_count = len(re.findall(r"\*\*Pergunta \d+:", full_content))
        if final_count < params['num_questions']:
            additional_qas = self.generate_additional_qas(
                doc_text, 
                params['num_questions'] - final_count, 
                params
            )
            full_content += "\n\n" + additional_qas

        return self.clean_qa_content(full_content, params['num_questions'])
    
    def generate_additional_qas(self, doc_text: str, num_needed: int, params: Dict[str, Any]) -> str:
        """Gera questões adicionais para completar o total solicitado."""
        try:
            llm = ChatOpenAI(
                api_key=self.openai_api_key,
                temperature=params['temperature'],
                model=self.model_qa_generator,
                timeout=REQUEST_TIMEOUT
            )
            prompt = ChatPromptTemplate.from_template("""
            Gere no mínimo de {num_questions} perguntas e respostas adicionais seguindo as mesmas regras.
            Documento: {document_text}
            """)

            chain = prompt | llm
            result = chain.invoke({
                "num_questions": num_needed,
                "document_text": doc_text[-10000:]  # Últimos 10k caracteres
            })
            return result.content

        except Exception as e:
            print(f"Erro ao gerar complemento: {str(e)}")
            return ""
    
    def clean_qa_content(self, content: str, num_questions: int) -> str:
        """Limpa e organiza o conteúdo de Q&A gerado."""
        qa_pairs = []
        seen = set()

        # Regex melhorado para capturar pares completos
        pattern = r"(\*\*Pergunta \d+:\*\*.*?)(?=\n\*\*Pergunta \d+:\*\*|\Z)"

        for pair in re.findall(pattern, content, re.DOTALL):
            simplified = re.sub(r'\s+', ' ', pair).strip()
            if simplified not in seen:
                seen.add(simplified)
                qa_pairs.append(pair)
            if len(qa_pairs) >= num_questions:
                break

        return "\n\n".join(qa_pairs[:num_questions])
    
    def qa_to_documents(self, qa_content: str, collection_name: str) -> List[Document]:
        """Converte o conteúdo de Q&A em documentos para inserção no Qdrant."""
        documents = []
        qa_pairs = re.findall(r"(\*\*Pergunta \d+:\*\*.*?)(?=\n\*\*Pergunta \d+:\*\*|\Z)", qa_content, re.DOTALL)
        
        for i, pair in enumerate(qa_pairs):
            doc = Document(
                page_content=pair,
                metadata={
                    'type': 'qa_pair',
                    'collection': collection_name,
                    'index': i,
                    'source': 'qa_generator',
                    'file_name': f'qa_pair_{i+1}',
                    'created_at': time.strftime('%Y-%m-%dT%H:%M:%S')
                }
            )
            documents.append(doc)
        
        return documents

# Instância global do gerador
qa_generator = QAGenerator() 