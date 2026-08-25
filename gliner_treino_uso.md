# GLiNER — Guia de treino e uso (encoder BERTimbau)

**Versão:** 3.6.4  
**Data da alteração:** 2026-08-25

Este documento reúne o fluxo educacional de **inferência** e **treino** do GLiNER neste projeto: o que cada modelo faz, como subir o container Torch, o contrato do JSON BIO (IOB2), o job assíncrono, o checkpoint em disco e como passar a usar o modelo treinado.

Os exemplos seguem o padrão REST da aplicação (Flask em `http://localhost:5000`) e do serviço FastAPI (`gliner-bert` em `http://localhost:8080`).

> **Importante:** o `rag-demo-app` **não** instala PyTorch. NER pesado e treino vivem no container `gliner-bert`. Não copie `torch` para o `requirements.txt` da aplicação Flask.

Documentação curta do sistema (arquitetura e flags):  
[docs/gliner-bertimbau.md](docs/gliner-bertimbau.md)

Tela irmã (spaCy, sem Torch):  
[docs/entidades-tfidf-ner.md](docs/entidades-tfidf-ner.md)

---

## 1. O que é este guia

O GLiNER (Generalist and Lightweight Named Entity Recognition) reconhece entidades a partir de **rótulos em linguagem natural** (`pessoa`, `norma`, `material`), sem um conjunto fixo de tipos como o spaCy clássico (PER/ORG/LOC/MISC).

Neste repositório há **dois usos** na interface:

1. **Entidades (GLiNER)** — extrai spans dos chunks de uma collection no Qdrant (somente payload; não altera a collection).
2. **Treinar GLiNER** — envia um JSON BIO; o container treina um modelo GLiNER cujo **encoder** é o BERTimbau (`neuralmind/bert-base-portuguese-cased`) e grava um checkpoint em `volumes/gliner-checkpoints/`.

O checkpoint **não** entra sozinho na extração. Na tela **Entidades (GLiNER)** escolha a pasta em disco e clique em **Carregar** (ou, após o treino, **Usar na extração**). Isso chama `POST /reload` no container — **sem** editar o `.env` nem recriar o serviço. `GLINER_MODEL` no `.env` só define o modelo de **arranque**.

---

## 2. Três NER no projeto (não misturar)

| Tela / caminho | Motor | Onde roda | Torch? |
| -------------- | ----- | --------- | ------ |
| **Entidades (estudo)** | spaCy `pt_core_news_md` + regex | `rag-demo-app` | Não |
| **Entidades (GLiNER)** | BERTimbau NER + GLiNER (fusão) **ou** só o checkpoint treinado | container `gliner-bert` | Sim |
| **Treinar GLiNER** | Cabeça GLiNER do zero + encoder BERTimbau | mesmo container | Sim |

Não use `NER_BACKEND=gliner` na tela **Entidades (estudo)**. Essa tela é spaCy de propósito: o gancho em `src/ner_backends.py` não substitui o serviço FastAPI.

Não dá para “encaixar” o checkpoint HuggingFace `pierreguillou/ner-bert-base-cased-pt-lenerbr` (token classification) no GLiNER oficial (encoder DeBERTa + cabeça de spans) sem retreinar. O treino deste guia cria **um** modelo GLiNER com encoder BERTimbau.

Documentação GLiNER (upstream):  
https://github.com/urchade/GLiNER

BERTimbau (encoder):  
https://huggingface.co/neuralmind/bert-base-portuguese-cased

BERTimbau NER LeNER-BR (inferência clássica PER/ORG/LOC):  
https://huggingface.co/pierreguillou/ner-bert-base-cased-pt-lenerbr

---

## 3. Arquitetura

```text
Navegador
    │
    ▼
rag-demo-app (Flask, sem torch)
    │  GET  /api/gliner-bert/status
    │  POST /api/gliner-study
    │  POST /api/gliner-train
    │  GET  /api/gliner-train/status
    ▼
gliner-bert :8080 (FastAPI + PyTorch)
    │  GET  /health
    │  POST /extract
    │  POST /train
    │  GET  /train/status
    ▼
volumes/huggingface          ← cache HF (HF_HOME=/models)
volumes/gliner-checkpoints   ← checkpoints treinados (/models/checkpoints)
```

O Flask só faz **proxy HTTP** (`src/gliner_bert_client.py`). TF-IDF e regex de códigos (Lei, PC 1/2018, CNPJ, siglas) continuam no rag-demo.

URL interna na rede Compose:

```text
GLINER_BERT_URL=http://gliner-bert:8080
```

Na máquina host (curl, testes):

```text
http://localhost:8080
```

---

## 4. Variáveis de ambiente

No `.env` (veja `env.example`):

```env
# Liga o profile Compose e o proxy Flask
GLINER_BERT=true
GLINER_BERT_URL=http://gliner-bert:8080
GLINER_BERT_TIMEOUT=120

# Rótulos abertos enviados ao GLiNER na inferência
GLINER_LABELS=pessoa,organização,local,material,processo,norma,instituição

# GPU opcional (imagem CUDA). Mantenha GLINER_BERT=true
GLINER_TRAIN=false

# Depois do treino: carregar só o checkpoint (sem pipeline HuggingFace NER)
GLINER_TRAINED_ONLY=false

# Encoder usado no treino (não é o GLiNER pré-treinado urchade/...)
GLINER_ENCODER=neuralmind/bert-base-portuguese-cased

# Inferência padrão (Hub). Depois do treino, troque pelo caminho local:
# GLINER_MODEL=/models/checkpoints/gliner-bertimbau-pt
```

Variáveis lidas **só** pelo container `gliner-bert` (Compose):

| Variável | Padrão | Função |
| -------- | ------ | ------ |
| `BERTIMBAU_NER_MODEL` | `pierreguillou/ner-bert-base-cased-pt-lenerbr` | Pipeline NER clássico na inferência híbrida |
| `GLINER_MODEL` | `urchade/gliner_multi-v2.1` | GLiNER de inferência (Hub ou pasta de checkpoint) |
| `GLINER_THRESHOLD` | `0.4` | Limiar `predict_entities` |
| `GLINER_TRAINED_ONLY` | `false` | Se `true` e o checkpoint existir, não carrega o pipeline NER extra |
| `GLINER_CHECKPOINT_ROOT` | `/models/checkpoints` | Destino dos jobs de treino |
| `GLINER_ENCODER` | `neuralmind/bert-base-portuguese-cased` | Encoder do `GLiNERConfig` no treino |
| `HF_HOME` | `/models` | Cache Hugging Face (volume `volumes/huggingface`) |
| `GLINER_TRAIN_MAX_STEPS` | `200` | Padrão de `max_steps` se o JSON não informar |

O Flask lê `GLINER_BERT`, `GLINER_BERT_URL`, `GLINER_BERT_TIMEOUT`, `GLINER_LABELS` e `GLINER_STUDY_MAX_CHUNKS` em `src/config.py`. Sem `GLINER_BERT=true` o proxy devolve 503.

> **Importante:** `GLINER_MODEL` no treino **não** é o ponto de partida. O job instancia `GLiNER(GLiNERConfig(model_name=GLINER_ENCODER, ...))` — cabeça nova, encoder BERTimbau. O `urchade/gliner_multi-v2.1` só entra na **inferência padrão**, enquanto você não apontar o checkpoint.

---

## 5. Subir o serviço (CPU)

Inferência e treino já funcionam na imagem CPU. O treino é mais lento (batch 1).

```env
GLINER_BERT=true
GLINER_TRAIN=false
```

```bash
docker compose --profile gliner up -d --build rag-demo-app gliner-bert
```

O `setup.sh` sobe o profile `gliner` quando `GLINER_BERT=true`.

Primeira subida baixa BERTimbau NER + GLiNER multi para `volumes/huggingface`. Reserve ~4 GB de RAM para o container (`mem_limit: 4g` no Compose). O healthcheck tem `start_period` de 180 s.

Conferir:

```http
GET http://localhost:8080/health
```

Resposta típica (modelos no Hub, CPU):

```json
{
  "status": "ok",
  "models_loaded": true,
  "bertimbau_model": "pierreguillou/ner-bert-base-cased-pt-lenerbr",
  "gliner_model": "urchade/gliner_multi-v2.1",
  "labels": ["pessoa", "organização", "local", "material", "processo", "norma", "instituição"],
  "cuda_available": false,
  "train_available": true,
  "device": "cpu",
  "trained_only": false,
  "training": { "state": "idle", "job_id": null }
}
```

Pelo Flask (sempre HTTP 200; `available` diz se o Torch está utilizável):

```http
GET http://localhost:5000/api/gliner-bert/status
```

Os menus **Entidades (GLiNER)** e **Treinar GLiNER** ficam **sempre visíveis**. Se o container estiver desligado, a tela mostra um banner amarelo e desativa o botão.

---

## 6. GPU opcional

Não é obrigatório. Use só se houver NVIDIA + Docker GPU.

```env
GLINER_BERT=true
GLINER_TRAIN=true
```

```bash
docker compose --profile gliner-train up -d --build rag-demo-app gliner-bert-gpu
```

O serviço GPU usa `Dockerfile.gpu`, `mem_limit: 8g` e o **mesmo** `container_name: gliner-bert` (hostname interno inalterado). Não suba `gliner` e `gliner-train` ao mesmo tempo: os dois querem a porta 8080 e o mesmo nome de container.

No treino com CUDA o batch sobe para 4 e, se o hardware permitir, `bf16`. Na CPU: `use_cpu=true`, batch 1, sem fp16/bf16.

---

## 7. Menus na interface

| Menu | Função | Botão ativo quando |
| ---- | ------ | ------------------ |
| Entidades (GLiNER) | TF-IDF local + NER remoto nos chunks; seletor de Hub vs checkpoint | `GET /api/gliner-bert/status` → `available: true` |
| Treinar GLiNER | Upload JSON BIO + `max_steps` + nome do checkpoint | `train_available: true` (serviço no ar) |

Não espere o menu “aparecer só depois do health”. A partir da **v3.6.2** o lateral mostra os dois itens mesmo com o Torch off, para o aluno achar a tela.

---

## 8. Inferência: Entidades (GLiNER)

Fluxo:

```text
Collection Qdrant
    → Flask lê payloads (scroll, sem set_payload)
    → TF-IDF no rag-demo
    → POST /extract no gliner-bert (textos, até 8000 caracteres cada)
    → fusão BERTimbau + GLiNER (ou só GLiNER se trained_only)
    → regex de códigos no rag-demo
    → rascunho de golden set (mesmo formato da tela spaCy)
```

Na UI: escolha a collection, `max_chunks` (padrão 200, teto 2000) e `top_n`.

API Flask:

```http
POST /api/gliner-study
Content-Type: application/json

{
  "collection_name": "sua-collection",
  "max_chunks": 200,
  "top_n": 50
}
```

A resposta inclui `backend: "gliner_bert"`, `golden_set_draft`, TF-IDF e vizinhos (Antes/Depois), no mesmo espírito de `POST /api/entity-study`.

Limite de chunks no estudo GLiNER: `GLINER_STUDY_MAX_CHUNKS` (padrão 200) — menor que o spaCy (2000), porque cada texto vai ao Torch.

---

## 9. Fusão de spans (inferência híbrida)

Com `GLINER_TRAINED_ONLY=false` (padrão) o `/extract` faz:

1. Pipeline HuggingFace NER (BERTimbau LeNER-BR) — PER/ORG/LOC.
2. GLiNER com os rótulos de `GLINER_LABELS` (ou os enviados no body).
3. `merge_span_sources` (`services/gliner_bert/span_merge.py`): **BERTimbau vence** em PER/ORG/LOC sobrepostos; GLiNER preenche o restante (norma, material, processo, etc.) e PER/ORG/LOC que não colidirem.

Rótulos são normalizados (`pessoa` → `PER`, `organização` → `ORG`, …).

Com `GLINER_TRAINED_ONLY=true` e checkpoint válido, o pipeline NER extra **não carrega**. A saída é só o GLiNER treinado.

---

## 10. Contrato POST /extract (container)

```http
POST http://localhost:8080/extract
Content-Type: application/json

{
  "texts": [
    "O Tribunal de Contas analisou a extrusão."
  ],
  "labels": ["pessoa", "organização", "material"]
}
```

`labels` é opcional; o padrão é `GLINER_LABELS`.

Resposta:

```json
{
  "spans": [
    [
      {
        "text": "Tribunal de Contas",
        "label": "ORG",
        "start": 2,
        "end": 20,
        "source": "bertimbau",
        "score": 0.99
      }
    ]
  ],
  "labels": ["pessoa", "organização", "material"]
}
```

`source` vale `bertimbau` ou `gliner`. HTTP 503 se os modelos ainda não carregaram.

---

## 11. Contrato do JSON BIO (IOB2)

O treino **não** baixa corpora. Você monta (ou exporta) um JSON IOB2.

Formato preferido:

```json
{
  "label_map": {
    "ORGANIZACAO": "organização",
    "PESSOA": "pessoa"
  },
  "max_steps": 200,
  "output_name": "gliner-bertimbau-pt",
  "sentences": [
    {
      "tokens": ["O", "Tribunal", "de", "Contas", "analisou"],
      "ner_tags": ["O", "B-ORGANIZACAO", "I-ORGANIZACAO", "I-ORGANIZACAO", "O"]
    }
  ]
}
```

Regras:

- Tags: `O`, `B-ROTULO`, `I-ROTULO` (hífen ou underscore).
- `tokens` e `ner_tags` **mesmo comprimento**.
- `I-X` sem `B-X` precedente é **rejeitado**.
- Frases sem tokens são ignoradas; se nenhuma frase sobrar → erro 400.
- `label_map` opcional; há um mapa padrão (`PER`/`PESSOA` → `pessoa`, `ORG`/`ORGANIZACAO` → `organização`, legislação → `norma`, …) em `bio_to_gliner.py`.
- `validation` opcional: mesmo formato (lista de frases ou objeto com `sentences`). Sem `validation`, ~10% das frases vão para validação se houver **pelo menos 10**; com menos de 10, a validação **copia** o treino.
- Também aceita uma **lista** de `{tokens, ner_tags}` na raiz, ou um único objeto frase.
- `max_steps`: 1–20000 (padrão 200).
- `output_name`: só `[a-zA-Z0-9._-]`; vira pasta sob `/models/checkpoints`.

Arquivo de exemplo no repositório:

```text
services/gliner_bert/example_bio.json
```

---

## 12. Conversão BIO → formato GLiNER

O GLiNER treina com índices de **token inclusivos**, não offsets de caractere:

```json
{
  "tokenized_text": ["O", "Tribunal", "de", "Contas", "analisou"],
  "ner": [[1, 3, "organização"]]
}
```

`[1, 3, "organização"]` = tokens 1, 2 e 3 (`Tribunal de Contas`). Conversão em `services/gliner_bert/bio_to_gliner.py` (sem torch; coberta por `tests/test_bio_to_gliner.py`).

---

## 13. Treinar pela interface

1. Suba o `gliner-bert` (seção 5 ou 6).
2. Menu **Treinar GLiNER**.
3. Escolha um `.json` BIO.
4. `max_steps`: na CPU use 50–200 para um teste; treino longo pode levar horas.
5. Nome do checkpoint (padrão `gliner-bertimbau-pt`).
6. Enviar. A UI faz poll em `GET /api/gliner-train/status` a cada ~2,5 s.

Só **um** job por vez. Segundo envio com treino `running` → HTTP 409.

O Flask aceita `multipart/form-data` (`file`, `max_steps`, `output_name`) ou JSON no body. Teto de arquivo: 20 MB (`MAX_CONTENT_LENGTH`).

---

## 14. Treinar pela API

Flask (upload):

```http
POST /api/gliner-train
Content-Type: multipart/form-data

file: example_bio.json
max_steps: 200
output_name: gliner-bertimbau-pt
```

Flask (JSON):

```http
POST /api/gliner-train
Content-Type: application/json

{
  "sentences": [
    {
      "tokens": ["Maria", "Silva", "apresentou", "o", "parecer"],
      "ner_tags": ["B-PESSOA", "I-PESSOA", "O", "O", "O"]
    }
  ],
  "max_steps": 50,
  "output_name": "teste-cpu"
}
```

Direto no container:

```http
POST http://localhost:8080/train
Content-Type: application/json
```

(mesmo body)

Resposta imediata (job em thread):

```json
{
  "success": true,
  "state": "running",
  "job_id": "a1b2c3d4e5f6",
  "step": 0,
  "max_steps": 200,
  "message": "Convertidas 2 frases de treino; iniciando em CPU...",
  "output_dir": "/models/checkpoints/gliner-bertimbau-pt",
  "train_size": 2,
  "val_size": 2
}
```

Erros frequentes:

| HTTP | Motivo |
| ---- | ------ |
| 400 | JSON BIO inválido (`I-` órfão, tags, `label_map`) |
| 409 | Já existe treino em andamento |
| 413 | Arquivo maior que 20 MB (Flask) |
| 503 | `GLINER_BERT=false` ou container inacessível |

---

## 15. Status do job

```http
GET /api/gliner-train/status
```

```http
GET http://localhost:8080/train/status
```

Campos:

| Campo | Valores / significado |
| ----- | --------------------- |
| `state` | `idle` \| `running` \| `done` \| `error` |
| `job_id` | hex curto do job atual |
| `step` / `max_steps` | progresso (ao terminar, `step == max_steps`) |
| `message` | texto para a UI |
| `output_dir` | pasta no container |
| `error` | preenchido se `state=error` |
| `train_size` / `val_size` | frases convertidas |

O `GET /health` também inclui um resumo `training.state` / `training.job_id`.

Quando `state=done`:

```text
Checkpoint gravado em /models/checkpoints/gliner-bertimbau-pt
```

No host:

```text
volumes/gliner-checkpoints/gliner-bertimbau-pt/
```

Essa pasta **não** vai para o git.

---

## 16. O que o treino faz de fato

Em `services/gliner_bert/train_job.py`:

1. Converte o JSON BIO.
2. Cria `GLiNERConfig(model_name=GLINER_ENCODER, hidden_size=768, max_width=12, max_len=384, fine_tune=True, span_mode="markerV0")`.
3. Instancia `GLiNER(config)` — **não** `GLiNER.from_pretrained("urchade/...")`.
4. `model.train_model(...)` com `learning_rate=1e-5`, `others_lr=5e-5`, `save_total_limit=1`.
5. Salva em `output_dir`.

O encoder BERTimbau é baixado (ou lido do cache HF) na hora do job. A cabeça de spans GLiNER começa **do zero**. Poucos passos + poucas frases servem para validar o pipeline, não para um modelo de produção.

---

## 17. Usar o modelo treinado na inferência

**Versão:** 3.6.4  
**Data da alteração:** 2026-08-25

Depois que o job chega em `state=done`, o checkpoint já está em `volumes/gliner-checkpoints/<nome>/`. A extração **ainda** usa o modelo em memória até você trocar.

Pela interface (recomendado): tela **Treinar GLiNER** → **Usar na extração**, ou **Entidades (GLiNER)** → seletor **Modelo GLiNER** → pasta `(disco)` → **Carregar**.

O Flask chama `POST /api/gliner-reload` (`{"id": "<nome>"}`). O container carrega o GLiNER da pasta com `trained_only=true`. Para voltar ao híbrido, escolha **Padrão Hub** e **Carregar**. Recarregar no meio do treino devolve `409`.

`id: "hub"` restaura `urchade/gliner_multi-v2.1` + BERTimbau NER. O `.env` (`GLINER_MODEL`, `GLINER_TRAINED_ONLY`) só vale no **arranque**.

Opcional no arranque (o seletor da UI ainda pode trocar depois):

```env
GLINER_MODEL=/models/checkpoints/gliner-bertimbau-pt
GLINER_TRAINED_ONLY=true
```

Os rótulos de inferência (`GLINER_LABELS`) devem **bater** com os nomes **depois** do `label_map` (ex.: `organização`, não `ORGANIZACAO`).

---

## 18. O que não fazer

- Instalar `torch` no `rag-demo-app`.
- Esperar que o fim do treino troque sozinho o modelo da extração (use **Carregar** / **Usar na extração**).
- Usar `NER_BACKEND=gliner` na tela spaCy.
- Subir `profile gliner` e `profile gliner-train` juntos.
- Tratar 50 passos em 2 frases de exemplo como modelo de domínio.
- Versionar `volumes/huggingface` ou `volumes/gliner-checkpoints`.
- Pedir ao sistema que baixe LeNER-BR / HAREM / UlyssesNER automaticamente.

---

## 19. APIs (resumo)

Container `gliner-bert`:

```http
GET  /health
GET  /models
POST /reload
POST /extract
POST /train
GET  /train/status
```

rag-demo (porta 5000):

```http
GET  /api/gliner-bert/status
GET  /api/gliner-models
POST /api/gliner-reload
POST /api/gliner-study
POST /api/gliner-train
GET  /api/gliner-train/status
```

A tela spaCy continua só em:

```http
POST /api/entity-study
POST /api/entity-study/export
```

---

## 20. Recursos e tempo

| Cenário | RAM (ordem de grandeza) | Observação |
| ------- | ----------------------- | ---------- |
| Inferência CPU | ~4 GB (`mem_limit`) | Primeira carga baixa os pesos HF |
| Treino CPU | mesmo container | batch 1; dezenas/centenas de passos podem levar **horas** |
| Treino GPU | ~8 GB + VRAM | profile `gliner-train`; batch 4 |

Textos de inferência são cortados em 8000 caracteres no serviço.

---

## 21. Corpora só como referência para montar o JSON

O sistema **não** baixa datasets. Use corpora públicos para **anotar ou converter** o seu JSON:

| Corpus | Uso típico |
| ------ | ---------- |
| LeNER-BR | NER jurídico PT (pessoas, organizações, legislação) |
| HAREM / First HAREM | NER clássico em português |
| Paramopama | complemento HAREM |
| UlyssesNER-Br | domínio legislativo |

Converta para IOB2 com `tokens` + `ner_tags` e, se os rótulos forem `PER`/`ORG`, o `label_map` padrão já traduz para `pessoa`/`organização`.

---

## 22. Relação com o golden set (itens 29 e 30)

As duas telas de entidades geram **rascunho** (`query`, `category`, `candidate_points`). O avaliador confirma `relevant_points` antes de Recall@K / MRR (`ranx`). Encadear o rascunho GLiNER com `ranx` ainda é TO-DO.

Regex de códigos e TF-IDF são os mesmos da tela spaCy; muda só o NER.

Guia Qdrant (item 33) e golden set:  
[qdrant_manipulacao_analise_dados.md](qdrant_manipulacao_analise_dados.md)

---

## 23. Arquivos no repositório

| Caminho | Papel |
| ------- | ----- |
| `services/gliner_bert/app.py` | FastAPI: health, extract, train, models, reload |
| `services/gliner_bert/checkpoint_store.py` | Lista e valida pastas em `/models/checkpoints` |
| `services/gliner_bert/bio_to_gliner.py` | IOB2 → `{tokenized_text, ner}` |
| `services/gliner_bert/train_job.py` | Job em thread, `GLiNERConfig` BERTimbau |
| `services/gliner_bert/span_merge.py` | Fusão BERTimbau + GLiNER |
| `services/gliner_bert/example_bio.json` | Exemplo mínimo |
| `services/gliner_bert/Dockerfile` | CPU + extras `gliner[training]` |
| `services/gliner_bert/Dockerfile.gpu` | CUDA |
| `src/gliner_bert_client.py` | Cliente HTTP Flask |
| `src/entity_study_service.py` | `run_gliner_entity_study` |
| `app.py` | Rotas `/api/gliner-*` |
| `docker-compose.yml` | profiles `gliner` e `gliner-train` |
| `tests/test_bio_to_gliner.py` | Conversão sem torch |
| `tests/test_span_merge.py` | Fusão |
| `tests/test_checkpoint_store.py` | Listagem de checkpoints (sem torch) |
| `tests/test_gliner_bert_client.py` | Cliente com mock |

---

## 24. Troubleshooting

**Menus visíveis, botão cinza, banner amarelo**  
Container off ou `GLINER_BERT=false`. Ative a flag, recrie `rag-demo-app` e `gliner-bert` com `--profile gliner`.

**`/health` em `loading` ou timeout**  
Primeira descarga dos modelos. Veja logs: `docker logs -f gliner-bert`. Espere o `start_period` (até 3 min).

**Treino 409**  
Espere `state` diferente de `running`, ou recrie o container para zerar o job em memória.

**Treino `done`, mas Entidades (GLiNER) igual a antes**  
O treino não troca o modelo sozinho. Use **Usar na extração** ou o seletor + **Carregar**. Recarregar com treino `running` devolve 409.

**CUDA false com `GLINER_TRAIN=true`**  
O profile GPU precisa do runtime NVIDIA. Sem GPU, use o profile `gliner` (CPU).

**JSON 400 `I-... sem B-...`**  
Corrija a anotação IOB2 (cada entidade começa com `B-`).

**Flask 503 em `/api/gliner-train` com mensagem `GLINER_BERT=false`**  
O `rag-demo-app` lê o `.env` na criação do container. Depois de mudar a flag: `docker compose --profile gliner up -d --force-recreate rag-demo-app`.

---

## TO-DOs

- [ ] Publicar o checkpoint no Hugging Face Hub
- [ ] Encadear o rascunho de entidades GLiNER com `ranx` (Recall@K / MRR)
- [ ] Progresso fino de `step` durante o `train_model` (hoje o passo só fecha no fim)

## Melhorias realizadas

- [x] Profile Compose `gliner` e flag `GLINER_BERT` (2026-08-25)
- [x] Serviço FastAPI BERTimbau NER + GLiNER (2026-08-25)
- [x] Proxy Flask sem torch (2026-08-25)
- [x] Conversão JSON BIO → GLiNER e job `POST /train` (2026-08-25)
- [x] Treino em CPU (batch 1); GPU opcional via `gliner-train` (2026-08-25)
- [x] Inferência do checkpoint com `GLINER_TRAINED_ONLY` (2026-08-25)
- [x] Menus sempre visíveis; banner se o serviço estiver off (2026-08-25)
- [x] Guia de treino e uso neste arquivo (2026-08-25)
- [x] Seletor de checkpoint na UI e `POST /reload` sem reiniciar o container (2026-08-25)
