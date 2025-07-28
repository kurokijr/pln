# Documento de Requisitos do Produto – App RAG-Demo

## 1. Resumo Funcional

O **RAG-Demo** é uma aplicação educacional desenvolvida para alunos da disciplina de Processamento de Linguagem Natural (PLN). O objetivo principal é demonstrar, de forma prática, o funcionamento integrado de uma arquitetura baseada em Recuperação Aumentada por Geração (RAG), utilizando os serviços **Qdrant**, **MinIO**, **n8n** e **LLMs**. A aplicação permite o upload de arquivos, sua conversão em vetores armazenados em collections separadas por modelo e tema, e um chat com múltiplas sessões que consulta os vetores. Também permite a criação de perguntas e respostas em markdown, como forma de enriquecer a base vetorial.

## 2. Para quem é este aplicativo

Este aplicativo é voltado para **alunos de graduação ou pós-graduação** da disciplina de PLN, em cursos de Ciência de Dados, Computação ou áreas correlatas. Os usuários acessam o sistema sem autenticação, diretamente em um ambiente local de laboratório ou sala de aula.

## 3. Requisitos Funcionais

- [x] Upload de arquivos em formato PDF para conversão em markdown;
- [x] Vetorização dos textos convertidos via serviços orquestrados no n8n;
- [x] Armazenamento dos vetores no **Qdrant**, organizados em **collections por modelo e assunto**;
- [x] Interface web com chat baseado em RAG que acessa as coleções vetoriais;
- [x] Histórico de conversas e suporte a múltiplas sessões;
- [x] Interface para criação manual de conteúdo em markdown (perguntas e respostas), que também será vetorizado;
- [x] Integração com o MinIO para armazenar os arquivos brutos convertidos;
- [x] Deploy local via Docker Compose, com os seguintes serviços: `RAG-Demo App`, `n8n`, `Qdrant`, `MinIO`.

## 4. Histórias de Usuário

### 4.1 Upload de Documento
**Como um aluno**, quero fazer upload de um PDF para que seu conteúdo seja automaticamente convertido e vetorizado, permitindo que eu consulte informações posteriormente via chat.

### 4.2 Chat com Base Vetorial
**Como um aluno**, quero conversar com um assistente virtual que usa os vetores do conteúdo enviado, para tirar dúvidas sobre o material de aula.

### 4.3 Criação de Conteúdo Manual
**Como um aluno**, quero cadastrar perguntas e respostas em markdown, para que esse conteúdo seja vetorizado e adicionado ao meu repositório de conhecimento.

### 4.4 Diferenciação de Embeddings
**Como um desenvolvedor/usuário avançado**, quero que os vetores sejam organizados por modelo de embedding e tema, para evitar mistura de representações incompatíveis.

## 5. Interface do Usuário

A interface web será composta por:

- **Tela inicial** com formulário de upload de PDF;
- **Dashboard de Collections**, com visualização e filtros por modelo e assunto;
- **Editor de Perguntas e Respostas**, com campo de entrada em markdown;
- **Chat RAG com múltiplas sessões**, exibição em layout tipo chat e histórico de conversas;
- **Feedback visual** durante a vetorização (via WebSocket ou polling do n8n).

O design será minimalista e funcional, voltado para o uso em ambiente acadêmico.

---

