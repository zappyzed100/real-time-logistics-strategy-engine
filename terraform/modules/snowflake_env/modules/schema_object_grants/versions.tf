# variable 間のクロスバリデーション（grant_on_future が grant_on_all を参照）は
# Terraform 1.9 以上が必要なため、required_version を明示する。
terraform {
  required_version = ">= 1.9.0"
}
