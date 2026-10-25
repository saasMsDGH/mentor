FROM python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf AS builder
WORKDIR /build
COPY apps/api/requirements-runtime.lock ./
COPY .build/mentor/python-wheels /deps/wheels
RUN --network=none python -m pip install --no-cache-dir --no-index --find-links=/deps/wheels --require-hashes --prefix=/install -r requirements-runtime.lock \
    && PYTHONPATH=/install/lib/python3.11/site-packages python -m pip check
# Public tokenizer data is prepared and hash-validated before the offline build.
COPY .build/mentor/tokenizer-cache /opt/mentor/tokenizer

FROM python:3.11-slim-bookworm@sha256:f06d01d4ba3f8ad5af45a3ec87df19c1d317d8e8961edc0fabda61811af6f7cf
ARG SOURCE_REVISION=working-tree
LABEL org.opencontainers.image.source="https://github.com/saasMsDGH/mentor" \
      org.opencontainers.image.revision="${SOURCE_REVISION}"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    TIKTOKEN_CACHE_DIR=/opt/mentor/tokenizer \
    ENVIRONMENT=production AUTH_ENABLED=true DEPLOYMENT_MODE=multi_user \
    APP_AUTO_CREATE_TABLES=false APP_AUTO_SEED_SYSTEM=false \
    APP_RUN_SCHEDULER=false APP_RUN_ACTIVITY_ENGINE=false AMBIENT_MONITOR_ENABLED=false \
    CODE_SANDBOX_BACKEND=container ALLOW_INSECURE_PROCESS_SANDBOX=false \
    UPLOAD_DIR=/app/uploads LLM_REQUIRED=true
WORKDIR /app
RUN groupadd --gid 10001 mentor \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin mentor \
    && mkdir -p /app/uploads && chown 10001:10001 /app/uploads
COPY --from=builder /install /usr/local
COPY --from=builder /opt/mentor/tokenizer /opt/mentor/tokenizer
COPY --chown=10001:10001 apps/api/ ./
COPY LICENSE /usr/share/licenses/mentor/LICENSE
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/health/live', timeout=3)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
