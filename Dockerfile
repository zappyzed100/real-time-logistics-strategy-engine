FROM python:3.11-slim AS base

# uv binaries for deterministic and fast dependency management.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV TZ=Asia/Tokyo \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Keep runtime base minimal. Development-only tools are installed in the development stage.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    openssh-client \
    wget \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*


FROM base AS deps-dev
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project


FROM base AS deps-prod
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev


FROM base AS development

# Development toolchain: gh, git, terraform, tflint.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    git \
    curl \
    unzip \
    && wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && chmod 644 /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends terraform gh \
    && rm -rf /var/lib/apt/lists/*

RUN TFLINT_VERSION=v0.54.0 \
    && curl -sSL -o /tmp/tflint.zip "https://github.com/terraform-linters/tflint/releases/download/${TFLINT_VERSION}/tflint_linux_amd64.zip" \
    && unzip -q /tmp/tflint.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/tflint \
    && rm -f /tmp/tflint.zip

COPY --from=deps-dev /app/.venv /app/.venv
COPY . .

EXPOSE 8501 8000 3000
CMD ["sh"]


FROM base AS production

COPY --from=deps-prod /app/.venv /app/.venv
COPY . .

EXPOSE 8501 8000 3000
CMD ["sh"]
