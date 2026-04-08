# Deployment Guide

## Multi-stage Docker Build

This repository uses a single `Dockerfile` with two runtime targets:

- `development`: includes developer tooling (`gh`, `git`, `build-essential`, `clang`, `lld`, `cmake`, `terraform`, `tflint`)
- `production`: minimal runtime image for deployment

`docker-compose.yml` は `development` target を使うため、ローカルで C++ 実装をビルド・検証するだけなら `development` に toolchain を入れれば足ります。現状は `g++` 系を含む `build-essential` に加えて、比較用に `clang` と高速リンク向けの `lld`、ビルド定義用の `cmake` を入れています。将来 native extension を production image のビルド工程でコンパイルする場合は、`production` runtime ではなく `deps-prod` などのビルド側ステージに同等の toolchain を追加します。

## Local Development Build

`docker-compose.yml` is configured to build with `target: development`.

```bash
docker compose build
```

After build, verify developer tools are available:

```bash
docker compose run --rm streamlit g++ --version
docker compose run --rm streamlit clang++ --version
docker compose run --rm streamlit cmake --version
docker compose run --rm streamlit gh --version
docker compose run --rm streamlit git --version
docker compose run --rm streamlit tflint --version
```

## Production Build

Build a minimal production image:

```bash
docker build --target production -t real-time-logistics-strategy-engine:prod .
```

Run verification checks to ensure dev tools are not bundled:

```bash
docker run --rm real-time-logistics-strategy-engine:prod sh -lc 'command -v gh || echo "gh: not installed"'
docker run --rm real-time-logistics-strategy-engine:prod sh -lc 'command -v git || echo "git: not installed"'
```

## CI Recommendation

In CI, explicitly choose build target by job purpose:

- lint/test jobs that need tooling: `--target development`
- deployment image build/push: `--target production`

## Production Approval Flow (Issue #161)

The production deployment flow now requires only one manual approval.

### Trigger scope

- `terraform-prod-plan`
  - runs on `pull_request`, `push(main)`, and `workflow_dispatch` (when `run_prod_plan=true`)

### Approval gate

- `prod-approval-gate`
  - runs only on `push` to `main`
  - uses `environment: prod` (single approval point)
  - depends on `lint`, `test`, and `terraform-prod-plan`

### Auto-continue after approval

Once `prod-approval-gate` is approved, jobs continue automatically in this order:

1. `terraform-prod-apply`
2. `prod-loader-run`
3. `prod-dbt-run`
4. `prod-dbt-test`

### Operational effect

- Approval count for production deploy is reduced to one.
- Plan review remains possible before approval.
- Infrastructure apply and data pipeline execution are treated as one release unit.
