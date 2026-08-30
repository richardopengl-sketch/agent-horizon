param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory=$true)]
    [string]$Location,

    [string]$Environment = "agent-horizon-env",
    [string]$AppName = "agent-horizon",
    [string]$Subscription = ""
)

$ErrorActionPreference = "Stop"

Write-Host "== Agent Horizon -> Azure Container Apps ==" -ForegroundColor Cyan

if ($Subscription) {
    Write-Host "Selecting subscription: $Subscription"
    az account set --subscription $Subscription
}

Write-Host "Ensuring Container Apps CLI extension is installed..."
az extension add --name containerapp --upgrade | Out-Host

Write-Host "Registering required Azure resource providers..."
az provider register --namespace Microsoft.App | Out-Null
az provider register --namespace Microsoft.OperationalInsights | Out-Null

Write-Host "Deploying from local source..." -ForegroundColor Yellow
$fqdn = az containerapp up `
    --name $AppName `
    --resource-group $ResourceGroup `
    --location $Location `
    --environment $Environment `
    --source . `
    --ingress external `
    --target-port 8501 `
    --query properties.configuration.ingress.fqdn `
    --output tsv

if (-not $fqdn) {
    throw "Deployment completed without returning an FQDN. Check the Azure CLI output above."
}

Write-Host ""
Write-Host "Deployment complete." -ForegroundColor Green
Write-Host "Live demo: https://$fqdn" -ForegroundColor Green
