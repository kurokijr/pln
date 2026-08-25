# Qdrant — Guia rápido de manipulação e análise de dados

Este documento reúne comandos úteis para inspeção, manipulação de payloads, filtragem, visualização e análise de vetores no Qdrant.

Os exemplos seguem o padrão da Web UI / REST API do Qdrant e usam como referência uma collection no formato:

```text
d542304d-09e6-409f-93e0-e0a1f5f2b51e
```

> **Importante:** substitua o nome/ID da collection conforme necessário.

---

## 1. Listar collections

```http
GET collections
```

Documentação oficial:  
https://api.qdrant.tech/api-reference/collections/get-collections

---

## 2. Obter informações de uma collection

```http
GET collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e
```

Útil para verificar:

- quantidade de points;
- configuração dos vetores;
- vetores `dense`;
- vetores `sparse`;
- distância utilizada;
- configuração HNSW;
- estado da collection.

Documentação oficial:  
https://api.qdrant.tech/api-reference/collections/get-collection

---

# 3. Estrutura de um Point

Um Point no Qdrant pode possuir:

```json
{
  "id": "01031217-a272-4ea4-8096-371313bf6c3a",
  "payload": {
    "document_id": "f5e78b42-af0c-4548-978d-8262cb54de92",
    "chunk_index": 4,
    "content": "Texto do chunk...",
    "is_public": true,
    "metadata": {
      "filename": "documento.pdf",
      "chunk_size": 800,
      "chunk_overlap": 200
    }
  },
  "vector": {
    "dense": [...],
    "sparse": {
      "indices": [...],
      "values": [...]
    }
  }
}
```

Documentação oficial:  
https://qdrant.tech/documentation/concepts/points/

---

# 4. Dense vs Sparse

## Dense

Representa principalmente similaridade semântica.

Exemplo conceitual:

```json
"dense": [
  -0.021,
  0.183,
  -0.092
]
```

Um vetor dense possui dimensão fixa.

Exemplo:

```text
dense
Length: 1536
```

É adequado para consultas como:

```text
"aluguel de automóveis"
```

encontrarem textos contendo:

```text
"locação de veículos"
```

mesmo sem correspondência literal.

---

## Sparse

Representa principalmente correspondência lexical.

Estrutura:

```json
{
  "indices": [12, 381, 9021],
  "values": [0.73, 1.42, 0.91]
}
```

O Qdrant armazena apenas as posições não-zero.

É especialmente útil para:

- siglas;
- códigos;
- números de processo;
- nomes;
- expressões específicas;
- termos raros.

Documentação oficial:  
https://qdrant.tech/documentation/concepts/vectors/

---

# 5. Adicionar ou alterar campos no payload

Não é necessário recriar a collection nem recalcular os embeddings.

## Exemplo: marcar Points como `duplicidade`

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload?wait=true
```

```json
{
  "payload": {
    "study_group": "duplicidade"
  },
  "filter": {
    "must": [
      {
        "key": "content",
        "match": {
          "text": "duplicidade"
        }
      }
    ]
  }
}
```

O Point passa a possuir:

```json
{
  "study_group": "duplicidade"
}
```

sem alterar os vetores existentes.

Documentação oficial:  
https://api.qdrant.tech/api-reference/points/set-payload

---

# 6. Filtrar por duas ou mais expressões — AND

No Qdrant, `must` representa uma operação lógica **AND**.

Exemplo: marcar apenas chunks que contenham:

```text
"fonte EMBRAPII"
```

**E**

```text
"duplicidade"
```

Comando:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload?wait=true
```

```json
{
  "payload": {
    "study_group": "duplicidade fonte embrapii"
  },
  "filter": {
    "must": [
      {
        "key": "content",
        "match": {
          "text": "fonte EMBRAPII"
        }
      },
      {
        "key": "content",
        "match": {
          "text": "duplicidade"
        }
      }
    ]
  }
}
```

Lógica:

```text
content contém "fonte EMBRAPII"
AND
content contém "duplicidade"
```

Documentação oficial:  
https://qdrant.tech/documentation/concepts/filtering/

---

# 7. Filtrar por expressões alternativas — OR

No Qdrant, `should` representa uma operação lógica semelhante a **OR**.

```json
{
  "filter": {
    "should": [
      {
        "key": "content",
        "match": {
          "text": "fonte EMBRAPII"
        }
      },
      {
        "key": "content",
        "match": {
          "text": "fonte Empresa"
        }
      }
    ]
  }
}
```

Lógica:

```text
"fonte EMBRAPII"
OR
"fonte Empresa"
```

Documentação oficial:  
https://qdrant.tech/documentation/concepts/filtering/

---

# 8. Excluir resultados — NOT

Use `must_not`.

```json
{
  "filter": {
    "must_not": [
      {
        "key": "content",
        "match": {
          "text": "duplicidade"
        }
      }
    ]
  }
}
```

Lógica:

```text
NOT content contém "duplicidade"
```

---

# 9. Combinar AND, OR e NOT

Exemplo:

```text
(fonte EMBRAPII OR fonte Empresa)
AND duplicidade
NOT cancelado
```

```json
{
  "filter": {
    "must": [
      {
        "key": "content",
        "match": {
          "text": "duplicidade"
        }
      },
      {
        "should": [
          {
            "key": "content",
            "match": {
              "text": "fonte EMBRAPII"
            }
          },
          {
            "key": "content",
            "match": {
              "text": "fonte Empresa"
            }
          }
        ]
      }
    ],
    "must_not": [
      {
        "key": "content",
        "match": {
          "text": "cancelado"
        }
      }
    ]
  }
}
```

---

# 10. `match.text` não é SQL `LIKE`

O Qdrant não possui diretamente:

```sql
LIKE '%manufatura%'
```

Para campos textuais, utilize:

```json
{
  "key": "content",
  "match": {
    "text": "manufatura"
  }
}
```

Essa busca trabalha com tokens do índice textual.

Para frases:

```json
{
  "key": "content",
  "match": {
    "phrase": "manufatura aditiva"
  }
}
```

Documentação oficial:  
https://qdrant.tech/documentation/search/text-search/text-filtering/

---

# 11. Criar índice textual para `content`

Para filtros textuais frequentes, crie um índice `text`.

```http
PUT /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/index?wait=true
```

```json
{
  "field_name": "content",
  "field_schema": {
    "type": "text",
    "ascii_folding": true,
    "phrase_matching": true
  }
}
```

Isso permite utilizar:

```json
{
  "match": {
    "text": "manufatura aditiva"
  }
}
```

e:

```json
{
  "match": {
    "phrase": "manufatura aditiva"
  }
}
```

Documentação oficial:  
https://qdrant.tech/documentation/search/text-search/text-filtering/

---

# 12. Limpar campos experimentais do payload

Para remover `study_group` de todos os Points:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload/delete?wait=true
```

```json
{
  "keys": [
    "study_group"
  ],
  "filter": {}
}
```

Isso mantém:

```text
Point ID
dense vector
sparse vector
content
document_id
metadata
```

e remove somente:

```json
"study_group": "..."
```

Documentação oficial:  
https://api.qdrant.tech/api-reference/points/delete-payload

---

# 13. Remover `study_group` somente de um grupo

Exemplo:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload/delete?wait=true
```

```json
{
  "keys": [
    "study_group"
  ],
  "filter": {
    "must": [
      {
        "key": "study_group",
        "match": {
          "value": "duplicidade"
        }
      }
    ]
  }
}
```

---

# 14. Preparar grupos para análise visual

Uma abordagem útil é inicialmente classificar todos como:

```text
outros
```

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload?wait=true
```

```json
{
  "payload": {
    "study_group": "outros"
  },
  "filter": {}
}
```

Depois sobrescrever os grupos desejados:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/payload?wait=true
```

```json
{
  "payload": {
    "study_group": "duplicidade"
  },
  "filter": {
    "must": [
      {
        "key": "content",
        "match": {
          "text": "duplicidade"
        }
      }
    ]
  }
}
```

---

# 15. Visualização por cor na Web UI

Depois de criar:

```json
"study_group": "duplicidade"
```

utilize:

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

A Web UI atribuirá cores diferentes para valores distintos de:

```text
study_group
```

Por exemplo:

```text
duplicidade
fonte-embrapii
fonte-empresa
outros
```

Documentação oficial:  
https://qdrant.tech/documentation/web-ui/

---

# 16. PCA

## 16.1 O que é PCA

PCA significa **Principal Component Analysis** ou **Análise de Componentes Principais**.

Seu objetivo é reduzir a dimensionalidade dos vetores tentando preservar, tanto quanto possível, as direções de maior variância dos dados.

Em uma collection com vetores `dense` de 1536 dimensões, cada Point pode ser imaginado como ocupando uma posição em um espaço com 1536 eixos.

Como não conseguimos visualizar 1536 dimensões diretamente, o PCA procura novas direções que resumem o máximo possível da variação presente nesses vetores.

Conceitualmente:

```text
1536 dimensões
      |
      v
identificação das direções de maior variância
      |
      v
Componente Principal 1
Componente Principal 2
      |
      v
gráfico 2D
```

Na Web UI:

```json
{
  "limit": 1000,
  "algorithm": "PCA",
  "using": "dense"
}
```

Com grupos:

```json
{
  "limit": 1000,
  "algorithm": "PCA",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

---

## 16.2 Como interpretar o PCA

No PCA, os eixos da visualização representam combinações das dimensões originais dos embeddings.

Se dois Points aparecem próximos:

```text
● ●
```

isso indica que eles possuem representação semelhante segundo as principais direções de variância capturadas pela projeção.

Se um Point aparece isolado:

```text
                  ●

● ● ● ● ● ● ●
```

isso pode indicar:

- conteúdo muito diferente dos demais;
- problema de extração textual;
- chunk atípico;
- documento fora do domínio predominante;
- conteúdo contendo tabelas, códigos ou caracteres anormais;
- possível erro no processo de embedding.

---

## 16.3 O que o PCA preserva melhor

O PCA tende a preservar melhor a **estrutura global** dos dados do que UMAP e t-SNE.

Isso significa que ele é particularmente útil para observar:

```text
formato geral da distribuição
grandes direções de separação
outliers
concentração dos dados
eventuais tendências globais
```

Por outro lado, ele é menos eficiente para evidenciar pequenos clusters semânticos quando a estrutura real dos embeddings é altamente não linear.

---

## 16.4 Limitação importante

PCA é uma transformação **linear**.

Embeddings modernos normalmente vivem em espaços com relações complexas e não lineares.

Assim, uma determinada estrutura pode existir no espaço original:

```text
A próximo de B
B próximo de C
C próximo de D
```

mas aparecer parcialmente misturada no PCA.

Isso não significa necessariamente que o embedding esteja ruim.

Significa apenas que uma projeção linear em duas dimensões não conseguiu representar toda a estrutura existente em 1536 dimensões.

---

## 16.5 Quando usar PCA

Use PCA principalmente para:

- criar um baseline visual;
- comparar collections;
- detectar outliers;
- identificar concentrações anormais;
- observar estrutura global;
- verificar se há grupos extremamente separados;
- analisar mudanças depois de trocar modelo de embedding.

Uma boa sequência de estudo é:

```text
PCA
 |
 |--> existem outliers?
 |--> existe um grande eixo de separação?
 |--> há regiões muito densas?
 |
 v
UMAP
```

---

# 17. UMAP

## 17.1 O que é UMAP

UMAP significa **Uniform Manifold Approximation and Projection**.

É um algoritmo não linear de redução de dimensionalidade desenvolvido para preservar principalmente a estrutura de vizinhança dos dados, mantendo também uma noção razoável da organização global.

No contexto de embeddings, a pergunta que o UMAP tenta representar é aproximadamente:

```text
"Quais vetores são vizinhos uns dos outros
e como esses grupos se relacionam?"
```

Na Web UI:

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense"
}
```

Com grupos:

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

---

## 17.2 Por que UMAP é especialmente útil para embeddings

Embeddings semânticos normalmente formam estruturas complexas.

Por exemplo, uma collection pode conter documentos sobre:

```text
prestação de contas
├── pessoal
├── viagens
├── equipamentos
└── serviços

propriedade intelectual
├── patente
├── software
└── licenciamento

tecnologia
├── inteligência artificial
├── manufatura aditiva
└── automação
```

No espaço de embeddings, esses assuntos podem formar regiões próximas, com transições entre temas relacionados.

O UMAP costuma representar esse tipo de estrutura de forma mais natural que o PCA.

Visualmente, você pode encontrar:

```text
      tecnologia
     ● ● ● ● ●
   ● ● ● ● ● ●

                    propriedade intelectual
                         ● ● ●
                       ● ● ● ●

prestação de contas
● ● ● ● ●
 ● ● ● ●
```

---

## 17.3 Como interpretar proximidade no UMAP

Quando dois Points aparecem próximos no UMAP, isso sugere que eles possuem vizinhanças semelhantes no espaço vetorial original.

Por exemplo:

```text
● "locação de veículos"
● "aluguel de automóveis"
● "contratação de veículos"
```

Se aparecem juntos, há uma evidência visual de que o embedding capturou corretamente a proximidade semântica.

Esse tipo de análise é particularmente útil quando combinada com `color_by`.

Exemplo:

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Suponha que você tenha:

```text
study_group = duplicidade
study_group = fonte-embrapii
study_group = fonte-empresa
study_group = outros
```

Você poderá observar se Points com a mesma classificação:

```text
ficam concentrados
ficam parcialmente agrupados
ou ficam completamente dispersos
```

---

## 17.4 O que significa um grupo bem formado

Imagine que todos os Points marcados como:

```text
study_group = "duplicidade"
```

apareçam concentrados nesta região:

```text
              ● ● ●
             ● ● ● ●
              ● ● ●
```

Isso sugere que os embeddings desses chunks possuem características semânticas semelhantes.

Se os mesmos Points aparecem assim:

```text
●                 ●

        ●

                          ●

   ●
```

pode significar várias coisas:

- o termo "duplicidade" aparece em contextos semanticamente diferentes;
- o modelo de embedding não está destacando esse conceito;
- os chunks contêm muito contexto adicional;
- a classificação por palavra-chave é lexical demais para representar uma classe semântica única.

Esse último caso é particularmente importante.

Um filtro textual como:

```json
{
  "match": {
    "text": "duplicidade"
  }
}
```

não garante que todos os chunks encontrados pertençam ao mesmo conceito semântico.

---

## 17.5 Estrutura local e estrutura global

UMAP tenta preservar melhor dois níveis:

```text
estrutura local
+
parte da estrutura global
```

Por exemplo:

```text
          manufatura aditiva
               ● ● ●
              ● ● ●

       automação
        ● ● ●
       ● ● ●

                           prestação de contas
                              ● ● ● ●
```

Você pode interpretar que:

```text
manufatura aditiva
e
automação
```

são regiões relacionadas.

Já uma região muito distante pode representar outro domínio documental.

Ainda assim, não trate distâncias do gráfico como métricas quantitativas exatas.

---

## 17.6 UMAP como visualização principal

Para análise exploratória de collections Qdrant, uma estratégia prática é usar UMAP como método principal.

Fluxo:

```text
UMAP
 |
 +--> identificar clusters
 |
 +--> colorir por payload
 |
 +--> inspecionar Points centrais
 |
 +--> inspecionar Points nas bordas
 |
 +--> inspecionar outliers
 |
 +--> comparar com Find Similar
```

Um Point na borda de um cluster pode ser particularmente interessante porque pode representar um documento que mistura dois assuntos.

---

## 17.7 Quando usar UMAP

Use UMAP principalmente para:

- visualizar organização semântica;
- identificar clusters;
- analisar transições entre assuntos;
- observar sobreposição entre categorias;
- comparar modelos de embedding;
- verificar se classificações conhecidas formam regiões coerentes;
- detectar Points que estão entre dois grupos.

Para estudos exploratórios de embeddings, normalmente é o algoritmo mais equilibrado dos três.

---

# 18. t-SNE

## 18.1 O que é t-SNE

t-SNE significa **t-distributed Stochastic Neighbor Embedding**.

Seu principal objetivo é preservar relações **locais**.

Em termos práticos, ele tenta garantir que Points que são vizinhos no espaço vetorial original continuem aparecendo próximos na representação 2D.

Na Web UI:

```json
{
  "limit": 1000,
  "algorithm": "TSNE",
  "using": "dense"
}
```

Com classificação:

```json
{
  "limit": 1000,
  "algorithm": "TSNE",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

---

## 18.2 Por que o t-SNE cria tantas "ilhas"

t-SNE é especialmente agressivo em destacar pequenas vizinhanças.

Por isso é comum obter algo assim:

```text
    ● ● ●


                        ● ●
                       ● ● ●


          ● ● ●
         ● ● ● ●


                              ● ● ●
```

Essas "ilhas" frequentemente representam grupos locais de Points similares.

Isso torna t-SNE excelente para responder:

```text
"Existem pequenos grupos bem definidos?"
```

Mas ruim para responder:

```text
"Qual é a distância real entre os grupos?"
```

---

## 18.3 A principal armadilha do t-SNE

Suponha:

```text
Cluster A                      Cluster B


             Cluster C
```

Não é correto concluir automaticamente que:

```text
A está semanticamente mais próximo de C do que de B
```

apenas porque a distância visual no gráfico é menor.

A posição relativa entre clusters no t-SNE pode ser fortemente influenciada pelo próprio processo de projeção.

Portanto:

```text
distância dentro do cluster -> geralmente útil
distância entre clusters    -> interpretar com cautela
```

---

## 18.4 O que significa um cluster no t-SNE

Suponha que você marque:

```text
study_group = "fonte-embrapii"
```

e todos os Points desse grupo apareçam juntos:

```text
● ● ● ●
 ● ● ●
● ● ● ●
```

Isso indica uma forte coerência local no espaço vetorial.

Mas você deve verificar os próprios textos dos Points.

Pode acontecer que o cluster tenha sido criado por outra característica comum:

```text
mesmo documento
mesma estrutura de formulário
mesma linguagem administrativa
mesmo cabeçalho
```

e não necessariamente pelo conceito que você está investigando.

Por isso, a análise visual deve sempre ser acompanhada por inspeção dos payloads.

---

## 18.5 Quando t-SNE é mais útil

Use t-SNE quando quiser investigar:

- pequenos grupos locais;
- duplicidades;
- documentos extremamente semelhantes;
- chunks quase repetidos;
- famílias de documentos;
- subgrupos dentro de um cluster maior.

Ele é especialmente interessante depois de você identificar uma região no UMAP.

Fluxo:

```text
UMAP
 |
 |--> encontrei uma região interessante
 |
 v
t-SNE
 |
 |--> quero inspecionar melhor a estrutura local
```

---

## 18.6 t-SNE e duplicidade

Para seu caso, t-SNE pode ser muito útil para estudar duplicidades.

Por exemplo:

```json
{
  "limit": 1000,
  "algorithm": "TSNE",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Se chunks classificados como:

```text
duplicidade
```

formarem vários pequenos grupos, isso pode significar que:

```text
o conceito aparece em diferentes contextos documentais
```

ou que existem:

```text
famílias diferentes de textos duplicados
```

---

# 19. Comparação PCA × UMAP × t-SNE

Os três algoritmos recebem os mesmos vetores.

Exemplo:

```text
dense vector
1536 dimensões
```

O que muda é apenas o método utilizado para transformá-los em duas dimensões.

```text
                         +--> PCA
                         |
1536 dimensões ----------+--> UMAP
                         |
                         +--> t-SNE
```

Portanto, se os gráficos parecerem completamente diferentes, isso não significa que os dados mudaram.

Apenas a forma de projeção mudou.

---

## 19.1 Comparação conceitual

| Característica | PCA | UMAP | t-SNE |
|---|---|---|---|
| Tipo | Linear | Não linear | Não linear |
| Estrutura local | Média | Alta | Muito alta |
| Estrutura global | Boa | Razoavelmente boa | Baixa |
| Outliers | Muito útil | Útil | Menos direto |
| Clusters locais | Moderado | Muito bom | Excelente |
| Distância entre clusters | Mais interpretável | Parcialmente interpretável | Pouco confiável |
| Velocidade | Geralmente maior | Intermediária | Geralmente menor |
| Uso principal | Baseline | Exploração | Vizinhança local |

---

## 19.2 Exemplo com a mesma collection

Imagine que sua collection contenha quatro temas:

```text
A = prestação de contas
B = pessoal e encargos
C = manufatura aditiva
D = propriedade intelectual
```

### PCA pode mostrar

```text
AAAAAAA BBBBBBB
 AAAA   BBBB

           CCCC
              CCCC

                     DDDD
```

Interpretação:

```text
existem grandes direções de separação
```

---

### UMAP pode mostrar

```text
AAAAAA---BBBBBB

        |
        |
      CCCCC

                    DDDDD
```

Interpretação:

```text
A e B parecem semanticamente relacionados
C forma uma região própria
D está relativamente isolado
```

---

### t-SNE pode mostrar

```text
AAAAA       BBBBB


       CCCCC


                       DDDDD
```

Interpretação:

```text
os quatro grupos possuem vizinhanças locais bem definidas
```

Mas não é correto medir visualmente:

```text
distância A-D
versus
distância A-C
```

como se fossem distâncias reais do embedding.

---

## 19.3 O que procurar nos três gráficos

### 1. Cluster consistente

Se um mesmo grupo aparece concentrado em:

```text
PCA
UMAP
t-SNE
```

isso é uma evidência visual forte de que existe alguma estrutura real associada àquele grupo.

---

### 2. Cluster apenas no t-SNE

Se um grupo só aparece perfeitamente separado no t-SNE:

```text
PCA  -> misturado
UMAP -> parcialmente misturado
TSNE -> perfeitamente separado
```

não conclua imediatamente que existe uma classe extremamente bem definida.

Pode ser efeito da ênfase do t-SNE sobre estrutura local.

---

### 3. Outlier consistente

Se um Point aparece isolado em PCA, UMAP e t-SNE:

```text
                     ●

● ● ● ● ● ● ●
```

vale inspecioná-lo.

Pode ser:

- extração defeituosa;
- conteúdo fora do domínio;
- chunk muito curto;
- caracteres estranhos;
- tabela;
- código;
- documento muito diferente;
- erro de embedding.

---

### 4. Grupos sobrepostos

Se duas categorias possuem cores diferentes mas aparecem misturadas:

```text
● ■ ● ■
■ ● ■ ●
● ■ ● ■
```

isso pode significar:

- os conceitos são semanticamente próximos;
- a classificação usada não corresponde à estrutura semântica;
- os chunks possuem muito contexto misturado;
- o modelo não separa esses conceitos;
- o critério de classificação é lexical e não semântico.

---

## 19.4 Procedimento recomendado para sua análise

Para cada collection:

### Passo 1 — PCA

```json
{
  "limit": 1000,
  "algorithm": "PCA",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Perguntas:

```text
Existem grandes separações?
Existem outliers?
Há concentração excessiva?
```

---

### Passo 2 — UMAP

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Perguntas:

```text
Quais temas formam regiões?
Quais grupos se sobrepõem?
Existem transições entre assuntos?
```

---

### Passo 3 — t-SNE

```json
{
  "limit": 1000,
  "algorithm": "TSNE",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Perguntas:

```text
Existem subgrupos?
Existem famílias de chunks muito semelhantes?
Os grupos conhecidos possuem coerência local?
```

---

### Passo 4 — Inspecionar Points

Depois de identificar um cluster:

```text
clicar no Point
      |
      v
ler content
      |
      v
ver document_id
      |
      v
ver filename
      |
      v
usar Find Similar
```

Essa etapa é fundamental.

O gráfico mostra uma hipótese.

O conteúdo do Point ajuda a explicar por que o cluster existe.

---

## 19.5 Regra prática

Para análise exploratória de embeddings:

```text
PCA
 |
 |--> "Como está a estrutura geral?"
 |
 v
UMAP
 |
 |--> "Quais regiões semânticas existem?"
 |
 v
t-SNE
 |
 |--> "Como são as pequenas vizinhanças?"
```

Ou, de forma resumida:

```text
PCA   -> visão macro
UMAP  -> estrutura semântica
t-SNE -> visão micro
```

Nenhum deles deve ser usado isoladamente como métrica de qualidade do RAG.

A confirmação deve ser feita por métricas de recuperação, como:

```text
Recall@K
MRR
nDCG
```

e por um conjunto de consultas com resultados relevantes conhecidos.

Documentação oficial da Web UI:  
https://qdrant.tech/documentation/web-ui/

# 20. Sparse não pode ser visualizado na Web UI

A Web UI atualmente não suporta:

```json
{
  "using": "sparse"
}
```

em PCA, UMAP ou t-SNE.

O erro apresentado é semelhante a:

```text
Vector visualization is not supported for vector type: sparse
```

Portanto:

```text
dense  -> visualização geométrica
sparse -> avaliação de recuperação/ranking
```

Documentação oficial sobre sparse vectors:  
https://qdrant.tech/documentation/concepts/vectors/

---

# 21. Busca somente no vetor Dense

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "using": "dense",
  "query": [
    0.023,
    -0.117,
    0.084
  ],
  "limit": 10,
  "with_payload": true
}
```

O vetor da query deve ter a dimensão definida para o named vector `dense`.

Documentação oficial:  
https://api.qdrant.tech/api-reference/search/query-points

---

# 22. Busca somente no vetor Sparse

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "using": "sparse",
  "query": {
    "indices": [
      234,
      852,
      1923
    ],
    "values": [
      1.83,
      0.97,
      2.21
    ]
  },
  "limit": 10,
  "with_payload": true
}
```

O sparse vector da consulta deve ser produzido pelo mesmo modelo/processo usado na indexação.

---

# 23. Hybrid Search — Dense + Sparse

O Qdrant permite combinar os dois mecanismos através de `prefetch`.

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "prefetch": [
    {
      "query": [
        0.023,
        -0.117,
        0.084
      ],
      "using": "dense",
      "limit": 50
    },
    {
      "query": {
        "indices": [
          234,
          852,
          1923
        ],
        "values": [
          1.83,
          0.97,
          2.21
        ]
      },
      "using": "sparse",
      "limit": 50
    }
  ],
  "query": {
    "fusion": "rrf"
  },
  "limit": 10,
  "with_payload": true
}
```

Fluxo:

```text
query
  |
  +--> dense  -> similaridade semântica
  |
  +--> sparse -> correspondência lexical
          |
          v
         RRF
          |
          v
   resultado combinado
```

Documentação oficial:  
https://qdrant.tech/documentation/concepts/hybrid-queries/

---

# 24. Aplicar filtro junto à busca

Exemplo: pesquisar somente documentos públicos.

```json
{
  "using": "dense",
  "query": [
    0.023,
    -0.117,
    0.084
  ],
  "filter": {
    "must": [
      {
        "key": "is_public",
        "match": {
          "value": true
        }
      }
    ]
  },
  "limit": 10,
  "with_payload": true
}
```

---

# 25. Filtrar por `document_id`

```json
{
  "filter": {
    "must": [
      {
        "key": "document_id",
        "match": {
          "value": "f5e78b42-af0c-4548-978d-8262cb54de92"
        }
      }
    ]
  }
}
```

É útil para restringir análises ou buscas a um documento específico.

---

# 26. Filtrar por campo dentro de `metadata`

Exemplo:

```json
{
  "filter": {
    "must": [
      {
        "key": "metadata.file_type",
        "match": {
          "value": "pdf"
        }
      }
    ]
  }
}
```

Também é possível filtrar outros campos:

```text
metadata.filename
metadata.collection_id
metadata.chunking_strategy
```

---

# 27. Estratégia sugerida para análise de uma collection

## Etapa 1 — Inventário

Obter:

```http
GET collections/{collection}
```

Registrar:

```text
points
dense vector size
sparse vector
distance
HNSW
quantização
```

---

## Etapa 2 — Qualidade dos chunks

Analisar payloads como:

```text
chunk_size
chunk_overlap
chunk_words
chunk_chars
chunk_sentences
```

Verificar:

- chunks muito pequenos;
- chunks muito grandes;
- duplicidades;
- texto extraído incorretamente;
- cabeçalhos e rodapés repetidos.

---

## Etapa 3 — Visualização Dense

Executar:

```json
{
  "limit": 1000,
  "algorithm": "PCA",
  "using": "dense"
}
```

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense"
}
```

```json
{
  "limit": 1000,
  "algorithm": "TSNE",
  "using": "dense"
}
```

---

## Etapa 4 — Criar grupos conhecidos

Exemplo:

```text
study_group
├── duplicidade
├── fonte-embrapii
├── fonte-empresa
├── pessoal-encargos
└── outros
```

Depois visualizar com:

```json
{
  "limit": 1000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Pergunta de análise:

```text
Os chunks pertencentes ao mesmo assunto ocupam regiões próximas no espaço vetorial?
```

---

# 28. Análise quantitativa — Dense × Sparse × Hybrid

A visualização não deve ser usada isoladamente para determinar a qualidade de um RAG.

Monte um conjunto de consultas reais:

```json
[
  {
    "query": "duplicidade de despesas",
    "relevant_points": [
      "uuid-point-1",
      "uuid-point-2"
    ]
  },
  {
    "query": "Pessoal e Encargos Sociais",
    "relevant_points": [
      "uuid-point-15"
    ]
  }
]
```

Execute cada consulta utilizando:

```text
Dense
Sparse
Hybrid
```

---

# 29. Métricas recomendadas — Recall@K e MRR

Para avaliar a qualidade da recuperação no Qdrant, a visualização por PCA, UMAP ou t-SNE é útil para exploração, mas não responde objetivamente à pergunta:

```text
"Os chunks corretos estão sendo recuperados?"
```

Para isso, é necessário trabalhar com um **golden set**: um conjunto de consultas para as quais já sabemos quais Points, documentos ou chunks são relevantes.

A documentação oficial do Qdrant recomenda essa abordagem para avaliação de relevância e cita explicitamente métricas como `Recall@K`, `MRR` e `NDCG@K`.

Referência oficial:

https://qdrant.tech/documentation/improve-search/retrieval-relevance/

---

## 29.1 Conceito de Golden Set

Um golden set é um conjunto de perguntas e respostas esperadas para o mecanismo de busca.

Exemplo:

```json
[
  {
    "query_id": "q1",
    "query": "despesas apresentadas em duplicidade",
    "relevant_points": [
      "point-123",
      "point-456"
    ]
  },
  {
    "query_id": "q2",
    "query": "regras para locação de veículos",
    "relevant_points": [
      "point-789"
    ]
  }
]
```

O campo:

```text
relevant_points
```

representa os Points que um avaliador humano considera corretos para aquela consulta.

Também é possível avaliar por:

```text
document_id
```

ou:

```text
metadata.filename
```

em vez do ID físico do Point.

Para RAG baseado em chunks, normalmente é mais preciso avaliar por Point ou `document_id + chunk_index`.

---

# 29.2 Recall@K

Recall@K responde:

> Entre todos os resultados relevantes conhecidos para a consulta, quantos apareceram entre os K primeiros resultados retornados?

A fórmula é:

```text
Recall@K =
quantidade de resultados relevantes encontrados no Top K
---------------------------------------------------------
quantidade total de resultados relevantes conhecidos
```

---

## 29.3 Exemplo simples de Recall@5

Suponha que, para a consulta:

```text
"despesas apresentadas em duplicidade"
```

o golden set diga que existem três Points relevantes:

```text
A
B
C
```

O Qdrant retorna:

```text
Rank  Point
----  -----
1     A
2     X
3     B
4     Y
5     Z
```

Nos cinco primeiros resultados foram encontrados:

```text
A
B
```

Dos três relevantes existentes:

```text
A
B
C
```

Portanto:

```text
Recall@5 = 2 / 3
         = 0,6667
         = 66,67%
```

Isso significa:

> O Qdrant conseguiu recuperar 66,67% dos resultados relevantes conhecidos dentro dos cinco primeiros resultados.

---

## 29.4 Exemplo de Recall@10

Se os resultados forem:

```text
Rank  Point
----  -----
1     A
2     X
3     B
4     Y
5     Z
6     W
7     C
8     K
9     L
10    M
```

Então:

```text
Recall@10 = 3 / 3
          = 1,0
          = 100%
```

Nesse caso, todos os resultados relevantes foram recuperados dentro do Top 10.

---

## 29.5 Por que Recall@K é especialmente importante para RAG

Imagine que sua aplicação envia os 10 chunks mais relevantes ao LLM.

Então a pergunta principal é:

```text
"O chunk que contém a informação necessária
está entre os 10 enviados ao modelo?"
```

Se sim, o LLM ainda pode produzir uma boa resposta.

Por isso, para um pipeline RAG que utiliza:

```text
top_k = 10
```

a métrica mais coerente é:

```text
Recall@10
```

A documentação oficial do Qdrant recomenda alinhar `K` ao número de resultados realmente consumidos pela aplicação.

Exemplo:

```text
Aplicação usa 5 chunks   -> Recall@5
Aplicação usa 10 chunks  -> Recall@10
Aplicação usa 20 chunks  -> Recall@20
```

Não é muito útil medir:

```text
Recall@100
```

se sua aplicação envia somente 5 chunks ao LLM.

---

# 29.6 MRR — Mean Reciprocal Rank

MRR significa:

```text
Mean Reciprocal Rank
```

ou:

```text
Média do inverso da posição
do primeiro resultado relevante
```

Enquanto Recall@K pergunta:

```text
"O resultado relevante apareceu?"
```

MRR pergunta:

```text
"Quão cedo apareceu o primeiro resultado relevante?"
```

A fórmula para uma consulta é:

```text
RR = 1 / posição do primeiro resultado relevante
```

Depois:

```text
MRR = média dos RR de todas as consultas
```

---

## 29.7 Exemplos de Reciprocal Rank

Se o primeiro resultado relevante estiver na posição 1:

```text
RR = 1 / 1
   = 1,00
```

Posição 2:

```text
RR = 1 / 2
   = 0,50
```

Posição 3:

```text
RR = 1 / 3
   = 0,3333
```

Posição 5:

```text
RR = 1 / 5
   = 0,20
```

Posição 10:

```text
RR = 1 / 10
   = 0,10
```

Quanto mais próximo de `1`, melhor.

---

## 29.8 Exemplo completo de MRR

Considere três consultas:

### Consulta Q1

```text
"duplicidade de despesas"
```

Primeiro resultado relevante:

```text
posição 1
```

Logo:

```text
RR1 = 1 / 1
    = 1,00
```

### Consulta Q2

```text
"regras para locação de veículos"
```

Primeiro relevante:

```text
posição 2
```

Logo:

```text
RR2 = 1 / 2
    = 0,50
```

### Consulta Q3

```text
"manufatura aditiva"
```

Primeiro relevante:

```text
posição 4
```

Logo:

```text
RR3 = 1 / 4
    = 0,25
```

MRR:

```text
MRR = (1,00 + 0,50 + 0,25) / 3

MRR = 1,75 / 3

MRR = 0,5833
```

Resultado:

```text
MRR = 0,5833
```

---

# 29.9 Recall@K e MRR medem coisas diferentes

Exemplo:

```text
Consulta: "duplicidade"
Resultado relevante na posição 5
```

Se:

```text
K = 5
```

então:

```text
Recall@5 = 1
```

porque o resultado relevante apareceu dentro do Top 5.

Mas:

```text
RR = 1/5 = 0,20
```

Ou seja:

```text
Recall@5 -> ótimo
MRR      -> relativamente baixo
```

Isso mostra que:

```text
Recall@K avalia cobertura
MRR avalia prioridade do primeiro acerto
```

Para RAG:

```text
Recall@K costuma ser prioritário
```

Para uma busca em que o usuário usa apenas o primeiro resultado:

```text
MRR ganha importância
```

---

# 29.10 Executando uma consulta Dense no Qdrant

Suponha que sua aplicação gere o seguinte embedding para:

```text
"duplicidade de despesas"
```

Exemplo ilustrativo:

```json
[
  0.012,
  -0.084,
  0.031
]
```

A consulta no Qdrant é:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "using": "dense",
  "query": [
    0.012,
    -0.084,
    0.031
  ],
  "limit": 10,
  "with_payload": true
}
```

> O vetor deve possuir exatamente a dimensão configurada no named vector `dense`. Os três valores acima são apenas ilustrativos.

O Qdrant retornará algo semelhante a:

```json
{
  "result": {
    "points": [
      {
        "id": "A",
        "score": 0.91,
        "payload": {
          "content": "Despesa desconsiderada por ter sido apresentada em duplicidade."
        }
      },
      {
        "id": "X",
        "score": 0.88,
        "payload": {
          "content": "Outro texto..."
        }
      }
    ]
  }
}
```

Para calcular Recall e MRR, o que interessa principalmente é:

```text
ordem dos IDs retornados
```

Documentação oficial:

https://api.qdrant.tech/api-reference/search/query-points

---

# 29.11 Executando uma consulta Sparse

Se o mesmo texto produzir:

```json
{
  "indices": [52, 817, 1203],
  "values": [1.42, 2.18, 0.91]
}
```

a consulta será:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "using": "sparse",
  "query": {
    "indices": [
      52,
      817,
      1203
    ],
    "values": [
      1.42,
      2.18,
      0.91
    ]
  },
  "limit": 10,
  "with_payload": true
}
```

Agora é possível calcular:

```text
Recall@5 Dense
Recall@10 Dense
MRR Dense

Recall@5 Sparse
Recall@10 Sparse
MRR Sparse
```

e comparar as estratégias.

---

# 29.12 Executando Hybrid Search

O Qdrant suporta combinação de resultados Dense + Sparse através da Query API.

Exemplo com RRF:

```http
POST /collections/d542304d-09e6-409f-93e0-e0a1f5f2b51e/points/query
```

```json
{
  "prefetch": [
    {
      "query": [
        0.012,
        -0.084,
        0.031
      ],
      "using": "dense",
      "limit": 50
    },
    {
      "query": {
        "indices": [
          52,
          817,
          1203
        ],
        "values": [
          1.42,
          2.18,
          0.91
        ]
      },
      "using": "sparse",
      "limit": 50
    }
  ],
  "query": {
    "rrf": {}
  },
  "limit": 10,
  "with_payload": true
}
```

O Qdrant executa:

```text
Dense search
      |
      +-----------+
                  |
Sparse search    |
      |           |
      +-----------+
                  |
                  v
                 RRF
                  |
                  v
              Top 10 final
```

O RRF combina posições de ranking dos diferentes retrievers.

Documentação oficial:

https://qdrant.tech/documentation/search/hybrid-queries/

---

# 29.13 Golden Set baseado em Point ID

Exemplo de arquivo:

```json
[
  {
    "query_id": "q001",
    "query": "duplicidade de despesas",
    "relevant_points": [
      "66b41b68-7ad6-42e2-8015-111111111111",
      "11c4771b-9aaf-4334-a17a-222222222222"
    ]
  },
  {
    "query_id": "q002",
    "query": "locação de veículos",
    "relevant_points": [
      "01031217-a272-4ea4-8096-371313bf6c3a"
    ]
  }
]
```

Essa abordagem é precisa quando sua unidade de recuperação é um chunk.

---

# 29.14 Golden Set baseado em documento

Às vezes vários chunks do mesmo documento podem responder corretamente.

Nesse caso, avaliar apenas Point ID pode penalizar injustamente o mecanismo.

Pode ser melhor marcar:

```json
{
  "query_id": "q002",
  "query": "locação de veículos",
  "relevant_document_ids": [
    "f5e78b42-af0c-4548-978d-8262cb54de92"
  ]
}
```

Então qualquer Point retornado com:

```json
{
  "document_id": "f5e78b42-af0c-4548-978d-8262cb54de92"
}
```

é considerado relevante.

Essa decisão deve refletir a arquitetura real do RAG.

---

# 29.15 Função Python simples para Recall@K

Exemplo independente:

```python
def recall_at_k(retrieved_ids, relevant_ids, k):
    retrieved_top_k = set(retrieved_ids[:k])
    relevant = set(relevant_ids)

    if not relevant:
        return 0.0

    hits = retrieved_top_k.intersection(relevant)

    return len(hits) / len(relevant)
```

Uso:

```python
retrieved = ["A", "X", "B", "Y", "Z", "C"]

relevant = ["A", "B", "C"]

print(recall_at_k(retrieved, relevant, 5))
```

Resultado:

```text
0.6666666666666666
```

Porque:

```text
relevantes = A, B, C
encontrados no Top 5 = A, B

2 / 3 = 0,6667
```

---

# 29.16 Função Python para Reciprocal Rank

```python
def reciprocal_rank(retrieved_ids, relevant_ids):
    relevant = set(relevant_ids)

    for rank, point_id in enumerate(retrieved_ids, start=1):
        if point_id in relevant:
            return 1.0 / rank

    return 0.0
```

Uso:

```python
retrieved = ["X", "A", "B", "C"]

relevant = ["A"]

print(reciprocal_rank(retrieved, relevant))
```

Resultado:

```text
0.5
```

porque `A` apareceu na posição 2:

```text
1 / 2 = 0,5
```

---

# 29.17 Função Python para MRR

```python
def mean_reciprocal_rank(results):
    scores = []

    for retrieved_ids, relevant_ids in results:
        scores.append(
            reciprocal_rank(
                retrieved_ids,
                relevant_ids
            )
        )

    if not scores:
        return 0.0

    return sum(scores) / len(scores)
```

Exemplo:

```python
results = [
    (
        ["A", "X", "Y"],
        ["A"]
    ),
    (
        ["X", "B", "Y"],
        ["B"]
    ),
    (
        ["X", "Y", "Z", "C"],
        ["C"]
    )
]

print(mean_reciprocal_rank(results))
```

Cálculo:

```text
Q1 -> 1/1 = 1,00
Q2 -> 1/2 = 0,50
Q3 -> 1/4 = 0,25
```

Logo:

```text
MRR = (1 + 0,5 + 0,25) / 3
    = 0,5833
```

---

# 29.18 Exemplo completo com Qdrant Client

O exemplo abaixo pressupõe que os embeddings da consulta já foram gerados pelo mesmo modelo usado na ingestão.

```python
from qdrant_client import QdrantClient

client = QdrantClient(
    url="http://localhost:6333"
)

COLLECTION = "d542304d-09e6-409f-93e0-e0a1f5f2b51e"


def search_dense(query_vector, limit=10):
    result = client.query_points(
        collection_name=COLLECTION,
        query=query_vector,
        using="dense",
        limit=limit,
        with_payload=True,
    )

    return [
        str(point.id)
        for point in result.points
    ]
```

Uso:

```python
query_vector = [
    # vetor real da consulta,
    # com a dimensão do seu modelo dense
]

ids = search_dense(
    query_vector,
    limit=10
)

print(ids)
```

---

# 29.19 Avaliando uma consulta individual

```python
relevant_ids = {
    "01031217-a272-4ea4-8096-371313bf6c3a"
}

retrieved_ids = search_dense(
    query_vector,
    limit=10
)

r5 = recall_at_k(
    retrieved_ids,
    relevant_ids,
    5
)

r10 = recall_at_k(
    retrieved_ids,
    relevant_ids,
    10
)

rr = reciprocal_rank(
    retrieved_ids,
    relevant_ids
)

print("Recall@5 :", r5)
print("Recall@10:", r10)
print("RR       :", rr)
```

Saída hipotética:

```text
Recall@5 : 1.0
Recall@10: 1.0
RR       : 0.5
```

Interpretação:

```text
O resultado correto apareceu no Top 5.
O resultado correto apareceu no Top 10.
O primeiro resultado correto estava na posição 2.
```

---

# 29.20 Avaliando várias consultas

Golden set:

```python
golden_set = [
    {
        "query_id": "q001",
        "query": "duplicidade de despesas",
        "dense_vector": [
            # embedding real
        ],
        "relevant_ids": {
            "point-A",
            "point-B"
        }
    },
    {
        "query_id": "q002",
        "query": "locação de veículos",
        "dense_vector": [
            # embedding real
        ],
        "relevant_ids": {
            "point-C"
        }
    }
]
```

Avaliação:

```python
rows = []

for item in golden_set:
    retrieved = search_dense(
        item["dense_vector"],
        limit=10
    )

    rows.append({
        "query_id": item["query_id"],
        "query": item["query"],
        "recall@5": recall_at_k(
            retrieved,
            item["relevant_ids"],
            5
        ),
        "recall@10": recall_at_k(
            retrieved,
            item["relevant_ids"],
            10
        ),
        "rr": reciprocal_rank(
            retrieved,
            item["relevant_ids"]
        )
    })
```

Depois:

```python
mean_recall_5 = sum(
    row["recall@5"]
    for row in rows
) / len(rows)

mean_recall_10 = sum(
    row["recall@10"]
    for row in rows
) / len(rows)

mrr = sum(
    row["rr"]
    for row in rows
) / len(rows)

print("Recall@5 :", mean_recall_5)
print("Recall@10:", mean_recall_10)
print("MRR       :", mrr)
```

---

# 29.21 Exemplo de relatório por consulta

Uma saída útil para análise pode ser:

```text
Query                           R@5    R@10    RR
--------------------------------------------------
duplicidade de despesas        1.00   1.00    1.00
locação de veículos            1.00   1.00    0.50
manufatura aditiva             0.00   1.00    0.14
propriedade intelectual        1.00   1.00    0.33
```

E o resumo:

```text
Recall@5  = 0,75
Recall@10 = 1,00
MRR       = 0,49
```

Interpretação:

```text
100% dos resultados relevantes aparecem no Top 10.

Apenas 75% aparecem no Top 5.

O primeiro resultado correto tende a aparecer
relativamente abaixo da primeira posição.
```

---

# 29.22 Comparando Dense × Sparse × Hybrid

O estudo fica mais útil quando a mesma golden set é executada contra três estratégias.

Estratégia 1:

```text
Dense
```

Estratégia 2:

```text
Sparse
```

Estratégia 3:

```text
Hybrid Dense + Sparse
```

Exemplo de resultado:

| Estratégia | Recall@5 | Recall@10 | MRR |
|---|---:|---:|---:|
| Dense | 0,78 | 0,88 | 0,61 |
| Sparse | 0,71 | 0,82 | 0,69 |
| Hybrid RRF | 0,89 | 0,95 | 0,77 |

Os valores acima são apenas ilustrativos.

Uma possível interpretação seria:

```text
Dense
-> boa cobertura semântica

Sparse
-> encontra resultados lexicais mais cedo

Hybrid
-> melhor cobertura e melhor posição média
```

---

# 29.23 Exemplo de função para comparar estratégias

Uma estrutura prática:

```python
def evaluate_strategy(
    golden_set,
    search_function,
    limit=10
):
    rows = []

    for item in golden_set:
        retrieved = search_function(
            item,
            limit=limit
        )

        rows.append({
            "query_id": item["query_id"],
            "recall@5": recall_at_k(
                retrieved,
                item["relevant_ids"],
                5
            ),
            "recall@10": recall_at_k(
                retrieved,
                item["relevant_ids"],
                10
            ),
            "rr": reciprocal_rank(
                retrieved,
                item["relevant_ids"]
            )
        })

    return {
        "recall@5": sum(
            x["recall@5"]
            for x in rows
        ) / len(rows),

        "recall@10": sum(
            x["recall@10"]
            for x in rows
        ) / len(rows),

        "mrr": sum(
            x["rr"]
            for x in rows
        ) / len(rows),

        "details": rows
    }
```

Isso permite fazer:

```python
dense_metrics = evaluate_strategy(
    golden_set,
    search_dense
)

sparse_metrics = evaluate_strategy(
    golden_set,
    search_sparse
)

hybrid_metrics = evaluate_strategy(
    golden_set,
    search_hybrid
)
```

---

# 29.24 Avaliação por `document_id` em vez de Point ID

Em RAG, pode ser necessário considerar qualquer chunk de determinado documento como relevante.

Função:

```python
def extract_document_ids(points):
    return [
        point.payload.get("document_id")
        for point in points
        if point.payload
    ]
```

Consulta:

```python
result = client.query_points(
    collection_name=COLLECTION,
    query=query_vector,
    using="dense",
    limit=10,
    with_payload=True
)

retrieved_document_ids = extract_document_ids(
    result.points
)
```

Golden set:

```python
relevant_document_ids = {
    "f5e78b42-af0c-4548-978d-8262cb54de92"
}
```

Então:

```python
recall_at_k(
    retrieved_document_ids,
    relevant_document_ids,
    10
)
```

---

# 29.25 Cuidado com múltiplos chunks do mesmo documento

Considere:

```text
Rank  document_id
----  -----------
1     DOC-A
2     DOC-A
3     DOC-A
4     DOC-B
5     DOC-C
```

Se você estiver avaliando documentos, contar `DOC-A` três vezes não faz sentido.

Faça deduplicação mantendo a ordem:

```python
def deduplicate_keep_order(values):
    return list(dict.fromkeys(values))
```

Uso:

```python
retrieved_document_ids = deduplicate_keep_order(
    retrieved_document_ids
)
```

Resultado:

```text
DOC-A
DOC-B
DOC-C
```

Isso é importante para não distorcer Recall@K por documento.

---

# 29.26 Quando um resultado não é encontrado

Se nenhum resultado relevante aparecer:

```text
Rank 1 -> X
Rank 2 -> Y
Rank 3 -> Z
...
```

então:

```text
RR = 0
```

Se existirem três relevantes no golden set e apenas um aparecer no Top 10:

```text
Recall@10 = 1 / 3
          = 0,3333
```

---

# 29.27 Exemplo prático com seus documentos

Imagine uma pergunta:

```text
"Por que uma despesa foi desconsiderada?"
```

Golden set:

```text
Point A:
"Despesa desconsiderada por ter sido apresentada em duplicidade."
```

Resultados Dense:

```text
1. Point X
2. Point Y
3. Point A
4. Point Z
5. Point W
```

Então:

```text
Recall@5 = 1,0
RR       = 1/3
RR       = 0,3333
```

Agora o Sparse retorna:

```text
1. Point A
2. Point X
3. Point Y
```

Então:

```text
Recall@5 = 1,0
RR       = 1,0
```

Hybrid retorna:

```text
1. Point A
2. Point Y
3. Point X
```

Então:

```text
Recall@5 = 1,0
RR       = 1,0
```

Para essa consulta específica, Sparse e Hybrid posicionaram o resultado relevante melhor.

---

# 29.28 Exemplo de consulta semântica

Consulta:

```text
"aluguel de automóveis"
```

Documento relevante contém:

```text
"locação de veículos"
```

Dense:

```text
Rank 1 -> relevante
```

Sparse:

```text
Rank 8 -> relevante
```

Então:

```text
Dense:
Recall@5 = 1
RR       = 1

Sparse:
Recall@5 = 0
RR       = 0,125
```

Isso mostra por que avaliar diferentes tipos de consulta é importante.

---

# 29.29 Separe o golden set por categoria

Não use somente uma média geral.

Classifique as consultas:

```text
semântica
lexical
sigla
código
nome próprio
frase exata
pergunta longa
pergunta curta
```

Exemplo:

```json
{
  "query_id": "q010",
  "category": "lexical",
  "query": "PC 1/2018",
  "relevant_points": [
    "point-A"
  ]
}
```

Depois calcule:

```text
Recall@10 Dense — lexical
Recall@10 Sparse — lexical
Recall@10 Hybrid — lexical

Recall@10 Dense — semântica
Recall@10 Sparse — semântica
Recall@10 Hybrid — semântica
```

Isso mostra onde cada estratégia realmente funciona.

---

# 29.30 Tamanho inicial recomendado para o estudo

Para uma primeira avaliação manual:

```text
30 a 50 consultas
```

Uma distribuição possível:

```text
10 consultas semânticas
10 consultas lexicais
10 consultas com códigos/siglas
10 consultas em linguagem natural
10 consultas difíceis/ambíguas
```

Depois evolua para:

```text
100+
```

consultas.

Quanto maior e mais representativo o golden set, mais confiável será a comparação.

---

# 29.31 Uso da biblioteca `ranx`

A documentação oficial do Qdrant utiliza a biblioteca Python `ranx` como exemplo para cálculo de métricas de ranking.

Instalação:

```bash
pip install ranx
```

Exemplo conceitual:

```python
from ranx import Qrels, Run, evaluate
```

Ground truth:

```python
qrels = Qrels({
    "q1": {
        "point-A": 1,
        "point-B": 1
    },
    "q2": {
        "point-C": 1
    }
})
```

Resultados da busca:

```python
run = Run({
    "q1": {
        "point-A": 0.91,
        "point-X": 0.88,
        "point-B": 0.85
    },
    "q2": {
        "point-X": 0.93,
        "point-C": 0.89
    }
})
```

Avaliação:

```python
metrics = evaluate(
    qrels,
    run,
    [
        "recall@5",
        "recall@10",
        "mrr"
    ]
)

print(metrics)
```

A documentação oficial do Qdrant recomenda esse tipo de fluxo para avaliação de relevância.

Referência:

https://qdrant.tech/documentation/improve-search/retrieval-relevance/

---

# 29.32 O score do Qdrant não substitui Recall ou MRR

Um erro comum é considerar:

```text
score = 0,92
```

como prova de que o resultado está correto.

O `score` significa apenas que, de acordo com aquela representação e métrica de similaridade, o Point possui alta similaridade com a consulta.

Ele não sabe se o resultado é realmente correto para seu caso de negócio.

Por isso:

```text
Qdrant score
!=
relevância humana
```

É o golden set que fornece a referência externa necessária para medir qualidade.

---

# 29.33 Score threshold também deve ser avaliado

Você pode utilizar:

```json
{
  "score_threshold": 0.7
}
```

em determinados tipos de consulta.

Porém, não escolha o threshold apenas visualmente.

Teste diferentes valores:

```text
0,50
0,60
0,70
0,80
```

e observe o impacto sobre:

```text
Recall@K
quantidade de resultados
latência
qualidade final
```

Threshold muito alto pode eliminar resultados relevantes.

Threshold muito baixo pode aceitar excesso de ruído.

---

# 29.34 Procedimento recomendado para comparar configurações

Crie uma baseline:

```text
Modelo Dense A
chunk_size = 800
overlap = 200
top_k = 10
```

Meça:

```text
Recall@5
Recall@10
MRR
```

Depois altere apenas uma variável:

```text
Modelo Dense B
```

e repita.

Depois:

```text
chunk_size = 1200
```

e repita.

Depois:

```text
Hybrid Dense + Sparse
```

e repita.

Isso permite atribuir a mudança da métrica à configuração modificada.

Evite mudar simultaneamente:

```text
embedding
chunking
retriever
top_k
reranker
```

porque ficará difícil identificar o motivo da melhoria ou piora.

---

# 29.35 Modelo de relatório final

Um relatório objetivo pode conter:

| Estratégia | Recall@5 | Recall@10 | MRR |
|---|---:|---:|---:|
| Dense | 0,78 | 0,88 | 0,61 |
| Sparse | 0,71 | 0,82 | 0,69 |
| Hybrid RRF | 0,89 | 0,95 | 0,77 |

E por categoria:

| Categoria | Dense R@10 | Sparse R@10 | Hybrid R@10 |
|---|---:|---:|---:|
| Semântica | 0,94 | 0,61 | 0,97 |
| Lexical | 0,72 | 0,93 | 0,96 |
| Códigos | 0,58 | 0,98 | 0,98 |
| Perguntas longas | 0,89 | 0,70 | 0,94 |

Os números são ilustrativos.

Esse segundo quadro costuma ser mais útil que apenas uma média geral.

---

# 30. Interpretação prática

## Recall@K alto + MRR alto

```text
Recall@10 = 0,96
MRR       = 0,85
```

Interpretação:

```text
quase todos os resultados relevantes aparecem
e normalmente aparecem cedo no ranking
```

É um cenário muito bom.

---

## Recall@K alto + MRR baixo

```text
Recall@10 = 0,95
MRR       = 0,38
```

Interpretação:

```text
o mecanismo encontra os resultados,
mas eles aparecem abaixo no ranking
```

Possíveis ações:

```text
reranking
Hybrid Search
ajuste de RRF
melhor embedding
melhor chunking
```

---

## Recall@K baixo + MRR alto

Exemplo:

```text
Recall@10 = 0,55
MRR       = 0,84
```

Pode ocorrer quando o primeiro resultado relevante aparece muito cedo, mas outros resultados relevantes não são recuperados.

Isso é importante quando uma consulta possui múltiplos documentos corretos.

---

## Recall@K baixo + MRR baixo

```text
Recall@10 = 0,42
MRR       = 0,29
```

É um sinal de problema mais estrutural.

Investigue:

```text
embedding model
chunking
qualidade do texto extraído
idioma
sparse model
filtros
conteúdo da collection
golden set
```

---

# 30.1 Regra prática para RAG

Para um pipeline que envia 10 chunks ao LLM:

```text
Métrica principal:
Recall@10

Métrica complementar:
MRR
```

Perguntas:

```text
Recall@10:
"O contexto necessário chegou ao LLM?"

MRR:
"O contexto correto aparece cedo no ranking?"
```

A documentação oficial do Qdrant recomenda `Recall@K` para pipelines RAG porque a presença do documento relevante dentro do conjunto entregue ao modelo costuma ser mais importante do que ele ocupar exatamente a primeira posição.

Referência oficial:

https://qdrant.tech/documentation/improve-search/retrieval-relevance/

# 30.2 Comparação visual entre duas collections

A Web UI do Qdrant não projeta nativamente Points de duas collections diferentes no mesmo gráfico PCA, UMAP ou t-SNE.

Para comparar duas collections visualmente, a abordagem mais prática é criar uma **collection temporária de estudo**, copiar uma amostra das duas collections e adicionar um campo de payload indicando a origem de cada Point.

Essa estratégia é segura porque:

```text
não altera as collections originais
não recalcula embeddings
não modifica os payloads originais
não exige reindexação das collections de produção
```

A comparação passa a ser feita em uma terceira collection criada especificamente para análise.

Documentação oficial:

https://qdrant.tech/documentation/concepts/collections/

---

## 30.2.1 Pré-requisito mais importante

Só combine diretamente os vetores de duas collections se eles pertencem ao **mesmo espaço vetorial**.

Na prática, isso significa que eles devem ter sido produzidos pelo mesmo modelo de embedding e possuir configuração compatível.

Exemplo válido:

```text
Collection A
dense size = 1536
modelo = embedding-X
distance = Cosine

Collection B
dense size = 1536
modelo = embedding-X
distance = Cosine
```

Nesse caso, os vetores podem ser colocados na mesma collection de estudo.

Exemplo que exige cautela:

```text
Collection A
dense size = 1536
modelo = embedding-X

Collection B
dense size = 1536
modelo = embedding-Y
```

Mesmo com a mesma dimensão, os espaços vetoriais podem não ser comparáveis.

Portanto:

```text
mesma dimensão != mesmo espaço vetorial
```

Exemplo incompatível:

```text
Collection A
dense size = 1536

Collection B
dense size = 3072
```

Esses vetores não podem ser simplesmente combinados na mesma configuração de vetor dense.

A configuração de uma collection define propriedades como:

```text
vector size
distance
named vectors
sparse vectors
```

Documentação oficial:

https://qdrant.tech/documentation/concepts/collections/

---

## 30.2.2 Criar uma collection temporária de comparação

Exemplo:

```http
PUT /collections/vector_comparison
```

```json
{
  "vectors": {
    "dense": {
      "size": 1536,
      "distance": "Cosine"
    }
  }
}
```

Substitua:

```text
1536
Cosine
```

pelas configurações reais das collections que serão comparadas.

Documentação oficial:

https://api.qdrant.tech/api-reference/collections/create-collection

---

## 30.2.3 Adicionar identificação de origem

Ao copiar os Points da primeira collection, acrescente ao payload:

```json
{
  "source_collection": "collection_A"
}
```

Ao copiar os Points da segunda:

```json
{
  "source_collection": "collection_B"
}
```

Um Point na collection de estudo pode ficar assim:

```json
{
  "id": "novo-ou-mesmo-id",
  "vector": {
    "dense": [
      0.012,
      -0.081,
      0.034
    ]
  },
  "payload": {
    "source_collection": "collection_A",
    "document_id": "f5e78b42-af0c-4548-978d-8262cb54de92",
    "chunk_index": 4,
    "content": "Texto do chunk...",
    "metadata": {
      "filename": "documento.pdf"
    }
  }
}
```

O campo:

```text
source_collection
```

será usado apenas para colorir a visualização.

---

## 30.2.4 Comparação por UMAP

Para esse tipo de análise, UMAP é normalmente a visualização mais útil.

```json
{
  "limit": 2000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "source_collection"
  }
}
```

Conceitualmente:

```text
● = Collection A
■ = Collection B
```

Se a visualização mostrar:

```text
● ■ ● ■ ●
■ ● ■ ● ■
● ■ ● ■ ●
```

isso sugere forte sobreposição entre as duas populações vetoriais.

Uma possível interpretação:

```text
as duas collections possuem conteúdo semanticamente semelhante
```

Se mostrar:

```text
● ● ● ● ● ●



                       ■ ■ ■ ■ ■ ■
```

isso sugere forte separação entre as duas collections.

Uma possível interpretação:

```text
as collections representam domínios semânticos diferentes
```

---

## 30.2.5 Comparação por PCA

Use:

```json
{
  "limit": 2000,
  "algorithm": "PCA",
  "using": "dense",
  "color_by": {
    "payload": "source_collection"
  }
}
```

O PCA é especialmente útil para comparar:

```text
distribuição global
amplitude dos vetores
outliers
grandes tendências
separação macro entre collections
```

Perguntas úteis:

```text
Uma collection ocupa uma região muito maior?

Uma collection possui mais outliers?

Existe uma direção principal que separa A de B?

As duas distribuições possuem formato semelhante?
```

---

## 30.2.6 Comparação por t-SNE

Use:

```json
{
  "limit": 2000,
  "algorithm": "TSNE",
  "using": "dense",
  "color_by": {
    "payload": "source_collection"
  }
}
```

O t-SNE é útil para observar:

```text
subgrupos locais
famílias de chunks
clusters pequenos
vizinhanças muito próximas
```

Porém, evite interpretar diretamente a distância entre clusters.

Exemplo:

```text
● ● ●          ■ ■ ■


        ● ■ ● ■


                         ■ ■ ■
```

O importante é analisar:

```text
se os clusters são mistos
ou
se cada cluster pertence quase exclusivamente a uma collection
```

---

## 30.2.7 Comparação por assunto e não apenas por collection

É possível adicionar mais de um campo experimental.

Exemplo:

```json
{
  "source_collection": "collection_A",
  "study_group": "duplicidade"
}
```

e:

```json
{
  "source_collection": "collection_B",
  "study_group": "duplicidade"
}
```

Primeiro visualize por origem:

```json
{
  "limit": 2000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "source_collection"
  }
}
```

Pergunta:

```text
As duas collections ocupam o mesmo espaço semântico?
```

Depois visualize pelos grupos de negócio:

```json
{
  "limit": 2000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "study_group"
  }
}
```

Pergunta:

```text
Os mesmos temas aparecem nas mesmas regiões,
independentemente da collection de origem?
```

---

## 30.2.8 Exemplo de comparação de estratégias de chunking

Essa técnica é muito útil para comparar duas collections criadas a partir do mesmo corpus com configurações diferentes.

Exemplo:

```text
Collection A
chunk_size = 800
chunk_overlap = 200

Collection B
chunk_size = 1200
chunk_overlap = 200
```

Na collection temporária:

```json
{
  "experiment": "chunk_800"
}
```

ou:

```json
{
  "experiment": "chunk_1200"
}
```

Visualização:

```json
{
  "limit": 2000,
  "algorithm": "UMAP",
  "using": "dense",
  "color_by": {
    "payload": "experiment"
  }
}
```

Isso permite investigar se uma estratégia produz:

```text
clusters mais compactos
maior dispersão
mais outliers
maior sobreposição temática
```

---

## 30.2.9 Exemplo de comparação de modelos de embedding

Se duas collections foram produzidas por modelos diferentes, não é recomendável simplesmente misturar os vetores no mesmo UMAP.

Exemplo:

```text
Collection A
modelo embedding A

Collection B
modelo embedding B
```

Mesmo que ambos tenham:

```text
1536 dimensões
```

eles podem representar espaços matematicamente distintos.

Nesse cenário, prefira:

```text
Collection A
   |
   v
UMAP A

Collection B
   |
   v
UMAP B
```

mantendo constantes:

```text
mesmo corpus
mesma amostra
mesmos grupos
mesmo limite
mesmo critério de seleção
```

Depois compare quantitativamente:

```text
Recall@5
Recall@10
MRR
nDCG@10
```

A avaliação de recuperação é mais confiável que a comparação puramente visual entre espaços produzidos por modelos diferentes.

---

## 30.2.10 Como copiar uma amostra com `qdrant-client`

Uma forma prática é usar `scroll` para ler Points de cada collection e inseri-los em uma collection temporária.

Exemplo conceitual:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

client = QdrantClient(
    url="http://localhost:6333"
)

SOURCE_A = "collection_A"
SOURCE_B = "collection_B"
TARGET = "vector_comparison"
```

Função para copiar Points:

```python
def copy_points(
    source_collection,
    source_label,
    target_collection,
    limit=1000
):
    points, _ = client.scroll(
        collection_name=source_collection,
        limit=limit,
        with_vectors=True,
        with_payload=True
    )

    new_points = []

    for point in points:
        payload = dict(point.payload or {})

        payload["source_collection"] = source_label

        new_points.append(
            PointStruct(
                id=point.id,
                vector=point.vector,
                payload=payload
            )
        )

    client.upsert(
        collection_name=target_collection,
        points=new_points
    )
```

Uso:

```python
copy_points(
    SOURCE_A,
    "collection_A",
    TARGET,
    limit=1000
)

copy_points(
    SOURCE_B,
    "collection_B",
    TARGET,
    limit=1000
)
```

> Se os IDs se repetirem entre as duas collections, gere novos IDs antes do `upsert`, caso contrário um Point poderá sobrescrever outro.

Documentação oficial do scroll:

https://api.qdrant.tech/api-reference/points/scroll-points

Documentação oficial do upsert:

https://api.qdrant.tech/api-reference/points/upsert-points

---

## 30.2.11 Evitar colisão de IDs

Duas collections podem conter o mesmo UUID.

Exemplo:

```text
Collection A
Point ID = abc-123

Collection B
Point ID = abc-123
```

Ao inseri-los em uma única collection:

```text
abc-123
```

só pode existir uma vez.

Uma abordagem é gerar novos IDs.

Exemplo:

```python
import uuid

new_id = str(uuid.uuid4())
```

E guardar o ID original:

```python
payload["original_point_id"] = str(point.id)
```

Além da origem:

```python
payload["source_collection"] = source_label
```

Assim:

```json
{
  "source_collection": "collection_A",
  "original_point_id": "abc-123"
}
```

---

## 30.2.12 Amostragem justa

Não compare:

```text
100 Points da Collection A
```

contra:

```text
10.000 Points da Collection B
```

porque a visualização pode ficar fortemente influenciada pela diferença de tamanho.

Prefira:

```text
1000 Points de A
1000 Points de B
```

ou, melhor ainda:

```text
mesmos documentos
mesmos grupos
mesma quantidade por grupo
```

Exemplo:

```text
duplicidade:
100 de A
100 de B

manufatura aditiva:
100 de A
100 de B

prestação de contas:
100 de A
100 de B
```

Isso reduz viés na interpretação visual.

---

## 30.2.13 O que procurar no gráfico

### Forte mistura

```text
●■●■■●■●
■●●■●■■●
```

Pode indicar:

```text
collections semanticamente semelhantes
```

---

### Separação completa

```text
●●●●●●



                       ■■■■■■
```

Pode indicar:

```text
domínios diferentes
processamento diferente
embedding diferente
chunking muito diferente
```

---

### Mesmos clusters, mas densidades diferentes

```text
●●●●●●
●●●●●

■■■
■■
```

Pode indicar:

```text
mesma temática,
mas uma das collections possui menor diversidade
ou menor cobertura
```

---

### Outliers exclusivos de uma collection

```text
●●●●■■■■

                         ●
```

Vale inspecionar o Point isolado.

Ele pode representar:

```text
erro de extração
chunk anormal
documento fora do domínio
conteúdo muito diferente
```

---

## 30.2.14 Fluxo recomendado

```text
Collection A
     |
     |
     +------------------+
                        |
                        v
                vector_comparison
                        ^
                        |
     +------------------+
     |
Collection B


vector_comparison
       |
       +--> source_collection
       |
       +--> study_group
       |
       v
      PCA
       |
       v
      UMAP
       |
       v
     t-SNE
       |
       v
inspeção de Points
       |
       v
Recall@K / MRR
```

A visualização deve ser usada como ferramenta exploratória.

A decisão sobre qual collection possui melhor qualidade de recuperação deve ser apoiada por métricas como:

```text
Recall@K
MRR
nDCG@K
```

e por um golden set comum às duas collections.


# 31. Fluxo recomendado de estudo

```text
COLLECTION
    |
    v
Inventário
    |
    v
Análise dos chunks
    |
    v
Visualização dense
    |
    +--> PCA
    +--> UMAP
    +--> t-SNE
    |
    v
Classificação temporária via payload
    |
    v
Análise de clusters
    |
    v
Golden Dataset
    |
    +--> Dense
    +--> Sparse
    +--> Hybrid
    |
    v
Recall@K / MRR / nDCG
    |
    v
Ajustes
    |
    +--> embedding model
    +--> chunk_size
    +--> overlap
    +--> filtros
    +--> HNSW
    +--> fusion
    +--> reranking
```

---

# 32. Referências oficiais do Qdrant

- Collections:  
  https://qdrant.tech/documentation/concepts/collections/

- Points:  
  https://qdrant.tech/documentation/concepts/points/

- Vectors:  
  https://qdrant.tech/documentation/concepts/vectors/

- Payload:  
  https://qdrant.tech/documentation/concepts/payload/

- Filtering:  
  https://qdrant.tech/documentation/concepts/filtering/

- Text Search / Text Filtering:  
  https://qdrant.tech/documentation/search/text-search/text-filtering/

- Query API:  
  https://api.qdrant.tech/api-reference/search/query-points

- Hybrid Queries:  
  https://qdrant.tech/documentation/concepts/hybrid-queries/

- Web UI:  
  https://qdrant.tech/documentation/web-ui/

- Set Payload:  
  https://api.qdrant.tech/api-reference/points/set-payload

- Delete Payload:  
  https://api.qdrant.tech/api-reference/points/delete-payload

---

# 33. Extração TF-IDF + NER (apoio aos itens 29 e 30)

**Versão:** 3.6.6  
**Data da alteração:** 2026-08-25

O golden set do item 29 pede consultas nas categorias `lexical`, `sigla`, `código` e `nome próprio`. A comparação visual do item 30 pede agrupamento por assunto (`study_group`), não só por collection.

A tela **Entidades (estudo)** da aplicação lê os chunks (somente payload, sem alterar a collection) e cruza:

```text
TF-IDF (termos distintivos)
  + NER spaCy 3.7+ pt_core_news_md (PER, ORG, LOC, MISC)
  + regex (Lei, PC 1/2018, CNPJ, siglas)
```

A partir da **v3.6.1** o treino GLiNER roda em **CPU** no profile `gliner` (GPU continua opcional).

A partir da **v3.5.0** existe a tela irmã **Entidades (GLiNER)**. O rag-demo **não** instala PyTorch: com `GLINER_BERT=true` o Compose sobe o profile `gliner` (container `gliner-bert`) com BERTimbau NER + GLiNER. O Flask só faz proxy HTTP (`GET /api/gliner-bert/status`, `POST /api/gliner-study`). A partir da **v3.6.2** os menus ficam sempre visíveis; se o container estiver desligado, a tela avisa e desativa o botão. Regex de códigos continua no rag-demo.

Guia de treino (JSON BIO) e uso do checkpoint: [gliner_treino_uso.md](gliner_treino_uso.md). Resumo do serviço: [docs/gliner-bertimbau.md](docs/gliner-bertimbau.md).

A saída é um **rascunho** de golden set no formato do item 29.1 (`query`, `category`, `candidate_points`). O avaliador confirma `relevant_points` antes de calcular Recall@K / MRR.

Na tabela **Top TF-IDF**, a leitura é Antes (top X) → Texto → Depois (top X): os tokens imediatos mais frequentes à esquerda e à direita (sem artigos e preposições), para ajudar a reconhecer entidades compostas. O **X** é o campo **Top vizinhos** (1–30, padrão 5) nas telas Entidades (estudo) e Entidades (GLiNER).

Não use spaCy 3.0: o projeto está em Python 3.12; o suporte começa na spaCy 3.7.

Documentação da funcionalidade:

[docs/entidades-tfidf-ner.md](docs/entidades-tfidf-ner.md)

API:

```http
POST /api/entity-study
{
  "collection_name": "sua-collection",
  "max_chunks": 2000,
  "top_n": 50,
  "neighbor_top": 5
}

GET /api/gliner-bert/status
GET /api/gliner-models
POST /api/gliner-reload
POST /api/gliner-study
{
  "collection_name": "sua-collection",
  "max_chunks": 200,
  "top_n": 50,
  "neighbor_top": 5
}
POST /api/gliner-train
GET /api/gliner-train/status
```
