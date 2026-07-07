param(
    [string]$ResourceGroup = "rg-prismguard-benchmark-law",
    [string]$Location = "eastus",
    [string]$AcrName = "prismguardlawbench"
)

$ErrorActionPreference = "Stop"
Write-Host "DRY-RUN: confirm with Director before executing az commands."
Write-Host "Would create RG=$ResourceGroup location=$Location and build 5 container images."
Write-Host "See benchmark/law/azure/README.md for full steps."
