# Documento de Design da Interface do Usuário – App RAG-Demo  
## Versão: Navegação Lateral Modular (Opção 1)

---

## Estrutura do Layout

- Interface com **menu lateral fixo** à esquerda, com ícones + texto.
- **Área de trabalho principal** ocupa o restante da tela, exibindo dinamicamente:
  - Tela de Upload
  - Dashboard de Collections
  - Editor de Perguntas e Respostas
  - Chat com múltiplas sessões
- Cabeçalho discreto com título da seção ativa e status geral

---

## Componentes Principais

### Menu Lateral
- Ícones + texto:  
  - 📄 `Upload`  
  - 📚 `Collections`  
  - ✍️ `Editor`  
  - 💬 `Chat`  
  - 🕓 `Histórico`  

### Tela de Upload
- Input para seleção de arquivo PDF  
- Dropdowns para escolher modelo e assunto  
- Botão de envio com barra de progresso e feedback  

### Dashboard de Collections
- Lista de collections com filtros (modelo, tema)  
- Informações: nome, tamanho, data de criação  
- Ação: excluir ou atualizar collection  

### Editor de Conteúdo
- Editor markdown com preview lateral  
- Campos para metadados: modelo, tema  
- Botão “Vetorização”  

### Chat
- Caixa de entrada com envio  
- Conversa formatada com markdown  
- Múltiplas sessões (navegáveis por aba ou lista lateral)  
- Respostas com feedback de tempo e consulta vetorial  

---

## Padrões de Interação

- Transição suave entre seções ao clicar no menu lateral  
- Feedback imediato após uploads e vetorização  
- Itens interativos com destaque ao passar o mouse  
- Mudança automática de estado visual: carregando / sucesso / erro  
- Toasts ou alertas no canto inferior para notificações  

---

## Elementos de Design Visual e Esquema de Cores

- Interface em tons de cinza com toques de azul e verde  
- Azul para ações principais (botões, links ativos)  
- Verde para vetorização bem-sucedida  
- Layout tipo painel administrativo (AdminLTE, VSCode-like)  
- Ícones simples e legíveis (usando uma biblioteca como Lucide ou Feather)  

---

## Considerações sobre Mobile, Web App e Desktop

- **Foco no uso em desktop e notebook**
- Responsivo apenas para tablets em modo paisagem  
- Acesso local via navegador (localhost), sem necessidade de autenticação  
- Layout de painel lateral não é recomendado para celulares  

---

## Tipografia

- Sem serifa, moderna: `Inter`, `Roboto`, `Helvetica Neue`  
- Títulos: 20–24px  
- Corpo: 14–16px  
- Monoespaçada: 13px para código markdown  
- Espaçamento generoso para ambiente de aula  

---

## Acessibilidade

- Navegação via teclado  
- Leitura por leitor de tela com uso de landmarks e `aria-labels`  
- Contraste suficiente para visibilidade (nível AA WCAG)  
- Ícones com descrição textual (tooltips e alt)  
- Feedbacks textuais visíveis para status de carregamento e erros  

---

## Wireframes em Texto – Opção 1

### 🧭 Layout Geral com Menu Lateral

+-----------------+--------------------------------------------+
| 📄 Upload | Título: [Upload de Documento] |
| 📚 Collections | |
| ✍️ Editor | [Selecionar PDF] [Dropdown: Modelo] |
| 💬 Chat | [Dropdown: Tema] [Botão: Enviar] |
| 🕓 Histórico | |
| | [Barra de Progresso] [Status] |
+-----------------+--------------------------------------------+

---

### 🗂️ Dashboard de Collections

+-----------------+--------------------------------------------+
| 📄 Upload | Título: [Collections] |
| 📚 Collections | |
| ✍️ Editor | [Filtro por Modelo] [Filtro por Tema] |
| 💬 Chat | |
| 🕓 Histórico | ┌────────────────────────────────────┐ |
| | │ Nome: aula1-distilB │ Tamanho │🗑️ │ |
| | └────────────────────────────────────┘ |
+-----------------+--------------------------------------------+

---

### ✍️ Editor de Perguntas e Respostas

+-----------------+--------------------------------------------+
| 📄 Upload | Título: [Editor de Perguntas] |
| 📚 Collections | |
| ✍️ Editor | Tema: [] |
| 💬 Chat | Modelo: [] |
| 🕓 Histórico | |
| | [Editor Markdown - à esquerda] |
| | [Pré-visualização - à direita] |
| | [Botão: Vetorizar Conteúdo] |
+-----------------+--------------------------------------------+

---

### 💬 Janela de Chat

+-----------------+--------------------------------------------+
| 📄 Upload | Título: [Chat RAG] |
| 📚 Collections | |
| ✍️ Editor | Sessão: [Selecionar ou Nova Sessão] |
| 💬 Chat | |
| 🕓 Histórico | 🧑: Qual a função do Milvus? |
| | 🤖: Milvus é um banco vetorial... |
| | |
| | [Campo de entrada de mensagem...] |
| | [Enviar] |
+-----------------+--------------------------------------------+

---

## Observações Finais

- Esse layout favorece **fluxo contínuo de trabalho**, permitindo alternância rápida entre envio, edição, exploração e conversação.
- Ideal para uso em sala de aula ou laboratório, mantendo **contexto visível** e sem ocultar etapas do processo.

