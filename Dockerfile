# --- Build Stage ---
FROM python:3.11 AS builder

# uvのインストール (再頒布性と速度のため、公式バイナリを使用)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 作業ディレクトリの設定
WORKDIR /app

# 依存関係ファイルのコピー
# キャッシュを効かせるため、ソースコードより先にコピーする
COPY pyproject.toml uv.lock ./

# 依存関係のインストール
# --mount=type=cache を使用してビルド速度を向上
# --frozen を使用して uv.lock と完全に一致させる
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# プロジェクト本体をインストールして、実行時のimport不整合を防ぐ
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- Runtime Stage ---
FROM python:3.11

# runtimeでも uv/uvx を利用できるようにする
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 開発コンテナ内で Git 操作できるように最低限のツールを入れる
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    gnupg \
    lsb-release \
    openssh-client \
    wget \
    && wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor > /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && chmod 644 /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" > /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends terraform \
    && rm -rf /var/lib/apt/lists/*

# 日本語ロケールやタイムゾーンが必要な場合はここで設定
ENV TZ=Asia/Tokyo \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    # Pythonが.pycファイルを作成しないようにする
    PYTHONDONTWRITEBYTECODE=1 \
    # ログがバッファリングされないようにする
    PYTHONUNBUFFERED=1 \
    # uvの仮想環境をPATHに追加
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# ビルドステージから仮想環境をコピー
COPY --from=builder /app/.venv /app/.venv

# ソースコードのコピー
COPY . .

# 各サービスのデフォルトポートを公開
# Streamlit: 8501
# FastAPI: 8000
# Dagster: 3000
EXPOSE 8501 8000 3000

# 実行コマンドは docker-compose.yml 側で
# サービス（Streamlit/FastAPI等）ごとに上書きすることを想定
CMD ["sh"]