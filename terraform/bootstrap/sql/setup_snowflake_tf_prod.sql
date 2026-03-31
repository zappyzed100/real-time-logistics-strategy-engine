-- =====================================================
-- Description: Snowflake Infrastructure Setup for Terraform (PROD)
-- Target: Production Environment
-- Author: Project Admin
-- =====================================================

USE ROLE ACCOUNTADMIN;

-- 一時ウェアハウス（bootstrap 専用・スクリプト末尾で削除）
CREATE WAREHOUSE IF NOT EXISTS PROD_BOOTSTRAP_TEMP_WH
  WAREHOUSE_SIZE = 'X-SMALL'
  AUTO_SUSPEND   = 60
  AUTO_RESUME    = TRUE
  INITIALLY_SUSPENDED = FALSE;
USE WAREHOUSE PROD_BOOTSTRAP_TEMP_WH;

-- =====================================================
-- Preflight checks + Terraform execution role/user setup
-- =====================================================
CREATE ROLE IF NOT EXISTS PROD_TF_ADMIN_ROLE;

EXECUTE IMMEDIATE $$
DECLARE
  -- ─── ユーザー入力欄（編集するのはここだけ）────────────────────────────
  -- [1] PROD_TFRUNNER_USER に設定する RSA 公開鍵
  --     256 バイトを超える鍵は SET 変数に格納できないため DECLARE 変数を使用
  runner_rsa_key_1  STRING := '<YOUR_PROD_RSA_PUBLIC_KEY_HERE>';
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
  EXECUTE IMMEDIATE 'CREATE USER IF NOT EXISTS PROD_TFRUNNER_USER RSA_PUBLIC_KEY = ''' || REPLACE(runner_rsa_key_1, '''', '''''') || ''' DEFAULT_ROLE = PROD_TF_ADMIN_ROLE';
  EXECUTE IMMEDIATE 'ALTER USER PROD_TFRUNNER_USER SET RSA_PUBLIC_KEY = ''' || REPLACE(runner_rsa_key_1, '''', '''''') || ''', DEFAULT_ROLE = PROD_TF_ADMIN_ROLE';

  IF (TRIM(runner_rsa_key_2) = '') THEN
    EXECUTE IMMEDIATE 'ALTER USER PROD_TFRUNNER_USER UNSET RSA_PUBLIC_KEY_2';
  ELSE
    EXECUTE IMMEDIATE 'ALTER USER PROD_TFRUNNER_USER SET RSA_PUBLIC_KEY_2 = ''' || REPLACE(runner_rsa_key_2, '''', '''''') || '''';
  END IF;
END;
$$;

-- 1. ロール・ユーザーへの権限付与
-- -----------------------------------------------------

GRANT ROLE PROD_TF_ADMIN_ROLE TO USER PROD_TFRUNNER_USER;

-- Terraform 実行に必要な権限を付与
-- 注意: MANAGE GRANTS はアカウント全体に対する権限であり、DEV/PRODが共用アカウントの場合はPRODロールがDEVオブジェクトにもGrant操作できる。
-- Terraformの GRANT ROLE TO ROLE (ロール階層) に必要なため付与するが、誤環境実行は必ず providers.tf の check ブロックで検出される。
GRANT CREATE DATABASE, CREATE WAREHOUSE, CREATE ROLE, CREATE USER, MANAGE GRANTS, CREATE NETWORK POLICY
  ON ACCOUNT TO ROLE PROD_TF_ADMIN_ROLE;

-- PROD では SYSADMIN への継承はデフォルト無効
-- 一時的なトラブルシュートが必要な場合は、チケット・期限付きで対応すること
-- GRANT ROLE PROD_TF_ADMIN_ROLE TO ROLE SYSADMIN;

-- 2. データレイヤー DB・スキーマ作成
-- -----------------------------------------------------
CREATE DATABASE IF NOT EXISTS PROD_BRONZE_DB;
ALTER DATABASE PROD_BRONZE_DB SET DATA_RETENTION_TIME_IN_DAYS = 90;
CREATE SCHEMA   IF NOT EXISTS PROD_BRONZE_DB.RAW_DATA WITH MANAGED ACCESS;
ALTER SCHEMA PROD_BRONZE_DB.RAW_DATA ENABLE MANAGED ACCESS;

CREATE DATABASE IF NOT EXISTS PROD_SILVER_DB;
ALTER DATABASE PROD_SILVER_DB SET DATA_RETENTION_TIME_IN_DAYS = 90;
CREATE SCHEMA   IF NOT EXISTS PROD_SILVER_DB.CLEANSED WITH MANAGED ACCESS;
ALTER SCHEMA PROD_SILVER_DB.CLEANSED ENABLE MANAGED ACCESS;

CREATE DATABASE IF NOT EXISTS PROD_GOLD_DB;
ALTER DATABASE PROD_GOLD_DB SET DATA_RETENTION_TIME_IN_DAYS = 90;
CREATE SCHEMA   IF NOT EXISTS PROD_GOLD_DB.MARKETING_MART WITH MANAGED ACCESS;
ALTER SCHEMA PROD_GOLD_DB.MARKETING_MART ENABLE MANAGED ACCESS;

-- 2.1 ネットワークポリシーは Terraform が直接作成・管理するため bootstrap では作成しない
-- （PROD_TF_ADMIN_ROLE に CREATE NETWORK POLICY 権限が付与されているため Terraform apply で自動作成される）
-- PROD_TFRUNNER_USER にはネットワークポリシーを適用しない
-- （JWT/RSA鍵ペア認証で保護。HCP Terraform ランナーは動的IPのため固定IPによる制限は不可）

-- 3. DB の所有権を PROD_TF_ADMIN_ROLE へ移譲
-- -----------------------------------------------------
GRANT OWNERSHIP ON DATABASE PROD_BRONZE_DB TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE PROD_SILVER_DB TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON DATABASE PROD_GOLD_DB TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;

-- 3.1 スキーマの所有権を PROD_TF_ADMIN_ROLE へ移譲
-- -----------------------------------------------------
GRANT OWNERSHIP ON SCHEMA PROD_BRONZE_DB.RAW_DATA TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA PROD_SILVER_DB.CLEANSED TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;
GRANT OWNERSHIP ON SCHEMA PROD_GOLD_DB.MARKETING_MART TO ROLE PROD_TF_ADMIN_ROLE COPY CURRENT GRANTS;

-- 一時ウェアハウスを削除
DROP WAREHOUSE IF EXISTS PROD_BOOTSTRAP_TEMP_WH;
