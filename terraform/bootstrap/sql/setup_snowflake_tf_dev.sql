-- =====================================================
-- Description: Snowflake Infrastructure Setup for Terraform (DEV)
-- Target: Development Environment
-- Author: Project Admin
-- =====================================================

USE ROLE ACCOUNTADMIN;

-- 一時ウェアハウス（bootstrap 専用・スクリプト末尾で削除）
CREATE WAREHOUSE IF NOT EXISTS DEV_BOOTSTRAP_TEMP_WH
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND   = 60
  AUTO_RESUME    = TRUE
  INITIALLY_SUSPENDED = FALSE;
USE WAREHOUSE DEV_BOOTSTRAP_TEMP_WH;

-- =====================================================
-- Preflight checks + Terraform execution role/user setup
-- =====================================================
CREATE ROLE IF NOT EXISTS DEV_TF_ADMIN_ROLE;

EXECUTE IMMEDIATE $$
DECLARE
  -- ─── ユーザー入力欄（編集するのはここだけ）────────────────────────────
  -- [1] DEV_TFRUNNER_USER に設定する RSA 公開鍵
  --     256 バイトを超える鍵は SET 変数に格納できないため DECLARE 変数を使用
  runner_rsa_key_1  STRING := '<YOUR_DEV_RSA_PUBLIC_KEY_HERE>';
  -- [3] ローテーション用の第 2 公開鍵（通常は空文字のまま）
  runner_rsa_key_2  STRING := '';
  -- ─── 派生変数（以下は編集不要）──────────────────────────────────────────
  err_not_accountadmin    EXCEPTION (-20001, 'ACCOUNTADMIN ロールで実行してください。');
  err_key1_placeholder    EXCEPTION (-20002, 'runner_rsa_key_1 を実値に置き換えてください。');
  err_key2_placeholder    EXCEPTION (-20003, 'runner_rsa_key_2 を実値に置き換えるか、空文字のままにしてください。');
BEGIN
  -- ロール確認
  IF (UPPER(CURRENT_ROLE()) <> 'ACCOUNTADMIN') THEN
    RAISE err_not_accountadmin;
  END IF;

  -- 公開鍵未置換チェック
  IF (TRIM(runner_rsa_key_1) = '' OR runner_rsa_key_1 LIKE '<%>') THEN
    RAISE err_key1_placeholder;
  END IF;

  IF (TRIM(runner_rsa_key_2) != '' AND runner_rsa_key_2 LIKE '<%>') THEN
    RAISE err_key2_placeholder;
  END IF;

  -- ユーザー作成・公開鍵設定
  EXECUTE IMMEDIATE 'CREATE USER IF NOT EXISTS DEV_TFRUNNER_USER RSA_PUBLIC_KEY = ''' || REPLACE(runner_rsa_key_1, '''', '''''') || ''' DEFAULT_ROLE = DEV_TF_ADMIN_ROLE';
  EXECUTE IMMEDIATE 'ALTER USER DEV_TFRUNNER_USER SET RSA_PUBLIC_KEY = ''' || REPLACE(runner_rsa_key_1, '''', '''''') || ''', DEFAULT_ROLE = DEV_TF_ADMIN_ROLE';

  IF (TRIM(runner_rsa_key_2) = '') THEN
    EXECUTE IMMEDIATE 'ALTER USER DEV_TFRUNNER_USER UNSET RSA_PUBLIC_KEY_2';
  ELSE
    EXECUTE IMMEDIATE 'ALTER USER DEV_TFRUNNER_USER SET RSA_PUBLIC_KEY_2 = ''' || REPLACE(runner_rsa_key_2, '''', '''''') || '''';
  END IF;
END;
$$;

-- 1. ロール・ユーザーへの権限付与
-- -----------------------------------------------------

GRANT ROLE DEV_TF_ADMIN_ROLE TO USER DEV_TFRUNNER_USER;

-- Terraform 実行に必要な権限を付与
-- 注意: MANAGE GRANTS はアカウント全体に対する権限であり、DEV/PRODが共用アカウントの場合はDEVロールがPRODオブジェクトにもGrant操作できる。
-- Terraformの GRANT ROLE TO ROLE (ロール階層) に必要なため付与するが、誤環境実行は必ず providers.tf の check ブロックで検出される。
GRANT CREATE DATABASE, CREATE WAREHOUSE, CREATE ROLE, CREATE USER, MANAGE GRANTS
  ON ACCOUNT TO ROLE DEV_TF_ADMIN_ROLE;

-- ガバナンス・可視性のため SYSADMIN へロールを継承
GRANT ROLE DEV_TF_ADMIN_ROLE TO ROLE SYSADMIN;

-- 2. データレイヤー DB・スキーマ作成
-- -----------------------------------------------------
CREATE DATABASE IF NOT EXISTS DEV_BRONZE_DB;
ALTER DATABASE DEV_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = 7;
CREATE SCHEMA   IF NOT EXISTS DEV_BRONZE_DB.RAW_DATA WITH MANAGED ACCESS;
ALTER SCHEMA DEV_BRONZE_DB.RAW_DATA ENABLE MANAGED ACCESS;

CREATE DATABASE IF NOT EXISTS DEV_SILVER_DB;
ALTER DATABASE DEV_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = 7;
CREATE SCHEMA   IF NOT EXISTS DEV_SILVER_DB.CLEANSED WITH MANAGED ACCESS;
ALTER SCHEMA DEV_SILVER_DB.CLEANSED ENABLE MANAGED ACCESS;

CREATE DATABASE IF NOT EXISTS DEV_GOLD_DB;
ALTER DATABASE DEV_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = 7;
CREATE SCHEMA   IF NOT EXISTS DEV_GOLD_DB.MARKETING_MART WITH MANAGED ACCESS;
ALTER SCHEMA DEV_GOLD_DB.MARKETING_MART ENABLE MANAGED ACCESS;

-- 2.1 ネットワークポリシーは運用対象外
-- DEV_TFRUNNER_USER にはネットワークポリシーを適用しない
-- （JWT/RSA鍵ペア認証で保護。実行元IPの固定 allowlist は前提にしない）

-- 3. DB の所有権を DEV_TF_ADMIN_ROLE へ移譲
-- -----------------------------------------------------
GRANT OWNERSHIP ON DATABASE DEV_BRONZE_DB TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE DEV_SILVER_DB TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE DEV_GOLD_DB TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;

-- 3.1 スキーマの所有権を DEV_TF_ADMIN_ROLE へ移譲
-- -----------------------------------------------------
GRANT OWNERSHIP ON SCHEMA DEV_BRONZE_DB.RAW_DATA TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA DEV_SILVER_DB.CLEANSED TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA DEV_GOLD_DB.MARKETING_MART TO ROLE DEV_TF_ADMIN_ROLE COPY CURRENT GRANTS;

-- 一時ウェアハウスを削除
DROP WAREHOUSE IF EXISTS DEV_BOOTSTRAP_TEMP_WH;
