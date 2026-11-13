# Hoshinoumi（REC）本机打完整 Docker 发布包
# 用法：
#   pwsh -File scripts/package_release_docker.ps1 -Version 20.0.0 `
#     -BotBase docker.m.daocloud.io/library/python:3.12-slim `
#     -GatewayBase docker.m.daocloud.io/library/ubuntu:24.04 `
#     -PipIndex https://pypi.tuna.tsinghua.edu.cn/simple
#
# 注意：必须在普通 PowerShell / Windows Terminal 里跑，
# 不要在 DSH 的低完整性 Python 子进程里调 docker build。

param(
    [string]$Version = "20.0.0",
    [string]$BotBase = "python:3.12-slim",
    [string]$GatewayBase = "ubuntu:24.04",
    [string]$PipIndex = "https://pypi.org/simple"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Release = Join-Path $Root "release"
New-Item -ItemType Directory -Force $Release | Out-Null
$BotTag = "hoshinoumi-bot:$Version"
$GwTag = "hoshinoumi-gateway:$Version"

Write-Host "==> 构建 bot 镜像 $BotTag" -ForegroundColor Cyan
docker build `
    --build-arg "BASE_IMAGE=$BotBase" `
    --build-arg "PIP_INDEX_URL=$PipIndex" `
    -t $BotTag .
if ($LASTEXITCODE -ne 0) { throw "bot 镜像构建失败" }

Write-Host "==> 构建 gateway 镜像 $GwTag" -ForegroundColor Cyan
docker build `
    -f gateway/Dockerfile.offline `
    --build-arg "BASE_IMAGE=$GatewayBase" `
    -t $GwTag .
if ($LASTEXITCODE -ne 0) { throw "gateway 镜像构建失败" }

Write-Host "==> 导出镜像" -ForegroundColor Cyan
$Raw = Join-Path $Release ".images.tar"
$Images = Join-Path $Release "REC-v${Version}-docker.tar.gz"
docker save $BotTag $GwTag -o $Raw
if ($LASTEXITCODE -ne 0) { throw "docker save 失败" }

# 用 Python 只做 gzip，不调用 docker（避免低完整性进程读 Docker 锁）
python -X utf8 -c "import gzip, shutil; shutil.copyfileobj(open(r'$Raw', 'rb'), gzip.open(r'$Images', 'wb'))"
Remove-Item $Raw -Force

Write-Host "==> 生成部署包" -ForegroundColor Cyan
$DeployName = "REC-v${Version}-deploy"
$Deploy = Join-Path $Release $DeployName
if (Test-Path $Deploy) { Remove-Item $Deploy -Recurse -Force }
New-Item -ItemType Directory -Force (Join-Path $Deploy "config") | Out-Null

Copy-Item docker-compose.release.yml (Join-Path $Deploy "docker-compose.yml")
Copy-Item .env.example (Join-Path $Deploy ".env.example")
Copy-Item gateway/config.example.json (Join-Path $Deploy "config/gateway.json")

$DeployTar = Join-Path $Release "${DeployName}.tar.gz"
Push-Location $Release
tar -czf "${DeployName}.tar.gz" $DeployName
Pop-Location

Write-Host ""
Write-Host "[OK] $Images" -ForegroundColor Green
Write-Host "[OK] $DeployTar" -ForegroundColor Green
Write-Host ""
Write-Host "部署机："
Write-Host "  docker load -i REC-v${Version}-docker.tar.gz"
Write-Host "  tar -xzf REC-v${Version}-deploy.tar.gz"
Write-Host "  cd $DeployName"
Write-Host "  cp .env.example .env"
Write-Host "  vi .env"
Write-Host "  docker compose up -d"

