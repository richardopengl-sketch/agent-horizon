# Deploy Agent Horizon to Azure Container Apps

This deployment publishes only the interactive Streamlit demo. Video-generation tooling (`automation/`, Playwright, Edge-TTS, MoviePy) is intentionally excluded from the runtime image.

## Files to copy into the repo root

- `Dockerfile`
- `.dockerignore`
- `requirements-runtime.txt`
- `deploy-azure.ps1`

## Prerequisites

- Azure CLI installed
- You can `az login`
- You have permission to deploy into the target subscription/resource group

## First deployment

From the Agent Horizon repo root:

```powershell
az login
az account show -o table

.\deploy-azure.ps1 `
  -Subscription "<subscription-name-or-id>" `
  -ResourceGroup "<resource-group>" `
  -Location "westus2" `
  -Environment "agent-horizon-env" `
  -AppName "agent-horizon"
```

The script uses `az containerapp up --source .`. Azure builds the Dockerfile, pushes the image, creates or reuses the Container Apps environment, enables external ingress, targets port 8501, and prints the HTTPS FQDN.

## Redeploy after code changes

Commit/push normally, then from your local repo root rerun the same deployment command:

```powershell
.\deploy-azure.ps1 `
  -Subscription "<subscription-name-or-id>" `
  -ResourceGroup "<resource-group>" `
  -Location "westus2" `
  -Environment "agent-horizon-env" `
  -AppName "agent-horizon"
```

`az containerapp up` can redeploy an existing app when the same resource group/environment/app name are supplied.

## Verify

```powershell
az containerapp show `
  --name agent-horizon `
  --resource-group <resource-group> `
  --query properties.configuration.ingress.fqdn `
  -o tsv
```

Open `https://<fqdn>`.

## Notes

- The demo uses synthetic fixtures only; do not add corporate secrets, credentials, tenant IDs, or private URLs.
- Port 8501 is internal to the container. Azure Container Apps exposes the app through HTTPS on its public FQDN when external ingress is enabled.
- For a hackathon demo, keeping the app stateless and deterministic is preferable to adding Azure service dependencies that do not support the core concept.
