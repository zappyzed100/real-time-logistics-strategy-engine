# Deployment Guide

## Multi-stage Docker Build

This repository uses a single `Dockerfile` with two runtime targets:

- `development`: includes developer tooling (`gh`, `git`, `terraform`, `tflint`)
- `production`: minimal runtime image for deployment

## Local Development Build

`docker-compose.yml` is configured to build with `target: development`.

```bash
docker compose build
```

After build, verify developer tools are available:

```bash
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
