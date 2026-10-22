# syntax=docker/dockerfile:1
# Stage 1 - resolve wheels (all runtime deps ship wheels; no gcc needed).
FROM python:3.11-slim AS wheels
ENV PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# Stage 2 - train the model at build time so the image is self-contained
# (Hugging Face Spaces cannot mount volumes; docker/ users still override
# models/ with their own volume, which shadows the baked default).
FROM python:3.11-slim AS train
ENV PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY --from=wheels /wheels /wheels
COPY requirements.txt .
# onnxmltools is only needed to export the trained XGBoost model to ONNX, so
# it is installed for the build and never reaches the runtime image.
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && pip install --no-cache-dir onnxmltools
COPY scripts ./scripts
RUN python scripts/train_model.py \
    && test -s models/fraud_model.onnx \
    && test -s models/fraud_model.pkl

# Stage 3 - slim runtime, non-root, stdlib healthcheck.
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY --from=wheels /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

COPY app ./app
COPY --from=train /app/models ./models

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p models data \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4); sys.exit(0)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
