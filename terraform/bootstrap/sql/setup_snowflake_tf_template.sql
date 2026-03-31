-- =====================================================
-- Description: Snowflake Infrastructure Setup for Terraform (Template)
-- Target: Parameterized (DEV/PROD)
-- Author: Project Admin
-- =====================================================
--
-- Usage:
-- 1) Replace all placeholders enclosed with <...>
-- 2) Save as environment-specific script
-- 3) Execute as ACCOUNTADMIN

USE ROLE ACCOUNTADMIN;

-- =====================================================
-- Required runtime inputs (replace placeholders before execution)
-- =====================================================
SET ENV_PREFIX                   = '<DEV_OR_PROD>'; -- DEV or PROD
SET EXPECTED_ACCOUNT             = '<ACCOUNT_IDENTIFIER>'; -- ex: ORG-PROD_ACCOUNT
SET RUNNER_RSA_PUBLIC_KEY        = '<RUNNER_RSA_PUBLIC_KEY_HERE>';
SET RUNNER_RSA_PUBLIC_KEY_2      = '<RUNNER_RSA_PUBLIC_KEY2_HERE>';
SET HCP_TERRAFORM_CIDR_1         = '<HCP_TERRAFORM_CIDR_1>';
SET CORPORATE_CIDR_1             = '<CORPORATE_CIDR_1>';
SET DATA_RETENTION_DAYS          = <RETENTION_DAYS>; -- DEV=7 / PROD=90

-- =====================================================
-- Preflight checks
-- =====================================================
EXECUTE IMMEDIATE $$
DECLARE
  env_prefix STRING := $ENV_PREFIX;
  expected_account STRING := $EXPECTED_ACCOUNT;
  pubkey_1 STRING := $RUNNER_RSA_PUBLIC_KEY;
  pubkey_2 STRING := $RUNNER_RSA_PUBLIC_KEY_2;
  hcp_cidr_1 STRING := $HCP_TERRAFORM_CIDR_1;
  corp_cidr_1 STRING := $CORPORATE_CIDR_1;
BEGIN
  IF UPPER(CURRENT_ROLE()) <> 'ACCOUNTADMIN' THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'Bootstrap must be executed as ACCOUNTADMIN.';
  END IF;

  IF env_prefix NOT IN ('DEV', 'PROD') THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'ENV_PREFIX must be DEV or PROD.';
  END IF;

  IF expected_account LIKE '<%>' THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'Replace EXPECTED_ACCOUNT placeholder before execution.';
  END IF;

  IF UPPER(CURRENT_ACCOUNT()) <> UPPER(expected_account) THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'Account mismatch. Stop to avoid cross-environment execution.';
  END IF;

  IF pubkey_1 LIKE '<%>' OR pubkey_2 LIKE '<%>' THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'Replace RUNNER_RSA_PUBLIC_KEY and RUNNER_RSA_PUBLIC_KEY_2 before execution.';
  END IF;

  IF hcp_cidr_1 LIKE '<%>' OR corp_cidr_1 LIKE '<%>' THEN
    RAISE STATEMENT_ERROR WITH MESSAGE => 'Replace network policy CIDR placeholders before execution.';
  END IF;
END;
$$;

-- NOTE:
-- For production, avoid broad role inheritance by default.
-- Apply temporary grants only under explicit approval and expiry.
