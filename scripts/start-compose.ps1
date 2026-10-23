$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not (Test-Path -LiteralPath '.env')) {
    $config = Get-Content -LiteralPath '.env.example' -Raw
    $secret = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(48))
    $config = $config.Replace('replace-with-a-random-secret-at-least-32-characters', $secret)
    Set-Content -LiteralPath '.env' -Value $config -Encoding utf8
}
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw '启动失败。请确认 Docker Desktop 已启动，且当前用户可以访问 Docker。' }
$frontendAddress = docker compose port frontend 80
Write-Output "工作台 http://$frontendAddress"
