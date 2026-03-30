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

# Development toolchain: gh, git, terraform, tflint, hadolint, shellcheck, taplo, yamllint, markdownlint-cli2, mermaid-cli.
ENV PUPPETEER_SKIP_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    git \
    curl \
    unzip \
    ripgrep \
    nodejs \
    npm \
    chromium \
    fonts-noto-cjk \
    shellcheck \
    yamllint \
    && wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && chmod 644 /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends terraform gh \
    && npm install -g markdownlint-cli2 @mermaid-js/mermaid-cli \
    && rm -rf /var/lib/apt/lists/*

RUN TFLINT_VERSION=v0.54.0 \
    && curl -sSL -o /tmp/tflint.zip "https://github.com/terraform-linters/tflint/releases/download/${TFLINT_VERSION}/tflint_linux_amd64.zip" \
    && unzip -q /tmp/tflint.zip -d /usr/local/bin \
    && chmod +x /usr/local/bin/tflint \
    && rm -f /tmp/tflint.zip

RUN HADOLINT_VERSION=v2.12.0 \
    && curl -sSL -o /usr/local/bin/hadolint "https://github.com/hadolint/hadolint/releases/download/${HADOLINT_VERSION}/hadolint-Linux-x86_64" \
    && chmod +x /usr/local/bin/hadolint

RUN TAPLO_VERSION=0.9.3 \
    && curl -sSL "https://github.com/tamasfe/taplo/releases/download/${TAPLO_VERSION}/taplo-linux-x86_64.gz" \
    | gzip -d > /usr/local/bin/taplo \
    && chmod +x /usr/local/bin/taplo

COPY --from=deps-dev /app/.venv /app/.venv
COPY . .

EXPOSE 8501 8000 3000
CMD ["sh"]


FROM base AS production

COPY --from=deps-prod /app/.venv /app/.venv
COPY . .

EXPOSE 8501 8000 3000
CMD ["sh"]
