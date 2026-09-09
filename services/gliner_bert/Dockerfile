FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-train.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt -r requirements-train.txt

COPY span_merge.py bio_to_gliner.py train_job.py checkpoint_store.py app.py example_bio.json ./

ENV HF_HOME=/models
ENV TRANSFORMERS_CACHE=/models
ENV HF_HUB_CACHE=/models/hub
ENV GLINER_CHECKPOINT_ROOT=/models/checkpoints

EXPOSE 8080

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
