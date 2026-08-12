FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY howlforge ./howlforge
COPY vault_template ./vault_template

RUN pip install --no-cache-dir .

ENV HOWLFORGE_VAULT_PATH=/app/vault
ENV HOWLFORGE_LLM_CONFIG=/app/howlforge/llm_config.yaml

VOLUME ["/app/vault"]

ENTRYPOINT ["howlforge"]
CMD ["doctor"]
