"""Processamento de documentos usando LangChain e LLMs."""

import os
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_core.documents import Document

from src.config import get_config

config = get_config()


class DocumentProcessor:
    """Processador de documentos com LLMs para melhorar a qualidade do texto."""
    
    def __init__(self):
        """Inicializa o processador de documentos."""
        self.llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=0.2
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "]
        )
    
    def load_document(self, file_path: str) -> str:
        """Carrega documento baseado na extensão do arquivo."""
        file_path = Path(file_path)
        extension = file_path.suffix.lower()
        
        try:
            if extension == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif extension == ".docx":
                loader = Docx2txtLoader(str(file_path))
            elif extension == ".txt":
                loader = TextLoader(str(file_path), encoding="utf-8")
            elif extension == ".md":
                loader = UnstructuredMarkdownLoader(str(file_path))
            else:
                raise ValueError(f"Extensão não suportada: {extension}")
            
            documents = loader.load()
            return "\n\n".join([doc.page_content for doc in documents])
            
        except Exception as e:
            raise Exception(f"Erro ao carregar documento {file_path}: {str(e)}")
    
    def enhance_text_with_llm(self, text: str) -> str:
        """Melhora a formatação do texto usando LLM."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em formatação de documentos técnicos. 
            Reformate o texto seguindo estas regras:

            1. **Estruturação lógica:**
               - Use headers hierárquicos (#, ##, ###)
               - Organize conteúdo relacionado em seções
               - Mantenha a ordem original das informações

            2. **Formatação consistente:**
               - Dados numéricos: padrão local (ex: R$ 1.234,56 ou 12.345,67 unidades)
               - Listas: use marcadores ou numeração quando apropriado
               - Tabelas: para dados tabulares com mais de 3 itens
               - Ênfase: use **negrito** para termos técnicos e _itálico_ para termos estrangeiros

            3. **Preservação de conteúdo:**
               - Nunca altere valores ou informações
               - Mantenha termos técnicos originais
               - Preserve referências a arquivos e metadados

            4. **Melhoria de legibilidade:**
               - Adicione espaçamento lógico entre seções
               - Quebras de linha para parágrafos longos
               - Links clicáveis quando detectar URLs

            Input: Texto Markdown cru extraído de documentos variados
            Output: Versão formatada seguindo padrões técnicos"""),
            ("human", "Texto original:\n{text}\n\nTexto reformatado:")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({"text": text})
            return response.content
        except Exception as e:
            # Se falhar, retorna o texto original
            return text
    
    def split_document(self, text: str) -> List[Document]:
        """Divide o documento em chunks menores."""
        return self.text_splitter.split_text(text)
    
    def process_document(self, file_path: str, enhance: bool = True) -> Dict[str, Any]:
        """Processa um documento completo."""
        try:
            # Carrega o documento
            raw_text = self.load_document(file_path)
            
            # Melhora o texto com LLM se solicitado
            if enhance:
                enhanced_text = self.enhance_text_with_llm(raw_text)
            else:
                enhanced_text = raw_text
            
            # Divide em chunks
            chunks = self.split_document(enhanced_text)
            
            # Adiciona metadados aos chunks
            documents = []
            for i, chunk in enumerate(chunks):
                doc = Document(
                    page_content=chunk,
                    metadata={
                        "source": Path(file_path).name,
                        "chunk_id": i,
                        "total_chunks": len(chunks),
                        "file_path": str(file_path),
                        "enhanced": enhance
                    }
                )
                documents.append(doc)
            
            return {
                "original_text": raw_text,
                "enhanced_text": enhanced_text,
                "chunks": documents,
                "total_chunks": len(documents),
                "file_name": Path(file_path).name,
                "file_size": len(raw_text)
            }
            
        except Exception as e:
            raise Exception(f"Erro ao processar documento: {str(e)}")


class QAGenerator:
    """Gerador de perguntas e respostas usando LLMs."""
    
    def __init__(self):
        """Inicializa o gerador de Q&A."""
        self.llm = ChatOpenAI(
            api_key=config.OPENAI_API_KEY,
            model=config.OPENAI_MODEL,
            temperature=0.7
        )
    
    def generate_qa_pairs(self, text: str, num_questions: int = 5, 
                         context_keywords: str = "", difficulty: str = "Intermediário") -> List[Dict[str, str]]:
        """Gera pares de perguntas e respostas baseados no texto."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """Você é um especialista em criação de conteúdos educacionais. 
            Gere {num_questions} perguntas e respostas baseadas no documento abaixo:

            REGRAS:
            1. Foco nos contextos: {context_keywords} (priorizar estes termos)
            2. Formato obrigatório: 
            **Pergunta {{número}}:** [texto] \\n\\n **Resposta {{número}}:** [texto]
            3. Nível de detalhe: adequado para profissionais de nível {difficulty}
            4. Inclua exemplos quando relevante
            5. As perguntas devem ser específicas e as respostas completas

            DOCUMENTO:
            {document_text}"""),
            ("human", "Gere as perguntas e respostas:")
        ])
        
        try:
            chain = prompt | self.llm
            response = chain.invoke({
                "num_questions": num_questions,
                "context_keywords": context_keywords,
                "difficulty": difficulty,
                "document_text": text
            })
            
            # Parse da resposta para extrair Q&A
            qa_pairs = self._parse_qa_response(response.content)
            return qa_pairs
            
        except Exception as e:
            raise Exception(f"Erro ao gerar Q&A: {str(e)}")
    
    def _parse_qa_response(self, response: str) -> List[Dict[str, str]]:
        """Parse da resposta do LLM para extrair perguntas e respostas."""
        import re
        
        qa_pairs = []
        pattern = r"\*\*Pergunta (\d+):\*\*(.*?)\*\*Resposta \1:\*\*(.*?)(?=\*\*Pergunta|\Z)"
        
        matches = re.findall(pattern, response, re.DOTALL)
        
        for match in matches:
            question_num, question, answer = match
            qa_pairs.append({
                "question": question.strip(),
                "answer": answer.strip(),
                "number": int(question_num)
            })
        
        return qa_pairs
    
    def generate_qa(self, text: str, num_questions: int = 5) -> Dict[str, Any]:
        """Gera perguntas e respostas a partir de texto."""
        try:
            qa_pairs = self.generate_qa_pairs(text, num_questions)
            return {
                "qa_pairs": qa_pairs,
                "total_qa": len(qa_pairs)
            }
        except Exception as e:
            raise Exception(f"Erro ao gerar Q&A: {str(e)}") 