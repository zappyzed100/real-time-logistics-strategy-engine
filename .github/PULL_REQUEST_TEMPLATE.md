# Pull Request

## 概要

<!-- 何を、なぜ変更したかを簡潔に記載 -->

## 背景

<!-- 変更の背景や課題。Issue があればリンク -->

## 変更内容

-

## 影響範囲

- [ ] Terraform
- [ ] dbt (`src/transform`)
- [ ] Loader / Streamlit / API
- [ ] CI/CD
- [ ] ドキュメントのみ

補足:

<!-- 影響対象の環境 (dev/prod) や関連システムを記載 -->

## テスト結果（エビデンス）

実行コマンド:

```bash
# 例
/app/.venv/bin/python src/scripts/quality/check_code_quality.py
```

実行結果:

```text
# 例
[check] python    | ok ...
```

## Terraform 変更時チェック

<!-- Terraform 変更がある場合は必須 -->

- [ ] `terraform -chdir=terraform fmt -check`
- [ ] `terraform -chdir=terraform validate`
- [ ] `tflint --chdir=terraform`
- [ ] 破壊的変更の有無を確認し、必要なら手順を記載

## データパイプライン変更時チェック

<!-- dbt / スキーマ変更がある場合は必須 -->

- [ ] `uv run python src/scripts/deploy/run_dbt.py deps`
- [ ] `uv run python src/scripts/deploy/run_dbt.py run`
- [ ] `uv run python src/scripts/deploy/run_dbt.py test`
- [ ] スキーマ変更時に `DATA_CONTRACT.md` を更新（未作成なら新規作成）

## ロールバック方針

<!-- 障害時に戻す方法を簡潔に記載 -->

## レビュー観点

<!-- レビュアーに重点確認してほしい点 -->

## 関連リンク

- Issue:
- その他:
