# Azure OIDC: replace expiring SAS credentials

This is an **independent, read-only smoke workflow**; existing SAS-backed download workflows remain unchanged. Do not enable unattended backfill until the OIDC workflow passes and a separate reviewed PR migrates the actual uploader/reader.

## 1. Azure: create a managed identity

Azure Portal -> **Managed identities** -> **Create** -> User-assigned managed identity. Name: `btc-quant-lab-github`. Place it in the existing resource group, Central India. Record **Client ID**, **Tenant ID** and Azure **Subscription ID**.

Assign **Storage Blob Data Contributor** to the identity **at the `btc-historical-data` container scope**. This includes data reading, listing and future uploads, but avoids granting broad account permissions. Identity should not be assigned Owner/Contributor to subscription.

## 2. Add GitHub federated credential

Open the managed identity -> **Federated credentials** -> **Add credential** -> **GitHub Actions deploying Azure resources**.

- GitHub owner: `unofficialallwyn-source`
- Repository: `btc-quant-lab`
- Entity type: **Branch**
- Branch: `main`
- Audience: `api://AzureADTokenExchange` (default)

The repository was renamed in October 2026. GitHub updated its default OIDC subject claim behavior for newly created or renamed repositories after July 15, 2026. **Check the actual GitHub OIDC `sub` claim and configure the federated credential to match; do not assume that the legacy textual `repo:owner/name:ref:refs/heads/main` always matches.** If login reports AADSTS700213, inspect actual GitHub claim and Azure credential mapping, never add wildcard trust.

## 3. Add three GitHub Actions secrets

Settings -> Secrets and variables -> Actions -> repository secrets:

- `AZURE_CLIENT_ID`: user-assigned managed identity Client ID
- `AZURE_TENANT_ID`: tenant / directory ID
- `AZURE_SUBSCRIPTION_ID`: subscription ID

These values are identifiers, not passwords, but repository secrets keep configuration centralized. Do not add a client secret, account key or SAS URL to the OIDC test.

## 4. Validate read-only login

Actions -> **Azure OIDC connectivity smoke test** -> Run workflow on `main` **only after this PR is merged**. It invokes azure/login v3, obtains a short-lived federated access token and lists BTC manifest names. This reads but does not modify Azure storage or exchange data.

If permissions were just granted, allow role propagation before testing. Test success confirms only login and list access—not uploads. After it passes, add a separate reviewed change to migrate the backfill upload and inventory clients to token-based authentication and run a bounded end-to-end test.

## Existing data and scope

The latest verified BTC uploads cover July 1–September 10, 2025 (72 days, 103,680 expected minute candles across successful intervals). This PR does not download new candles, renew the existing October 31 SAS, or change the daily controller opt-in variable. The daily controller must stay disabled during OIDC testing.
