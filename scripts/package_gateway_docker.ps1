# 只打包 C++ 网关镜像（不含 Python bot）
# 用法：
#   .\scripts\package_gateway_docker.ps1 -Version 20.0.0 `
#     -GatewayBase docker.m.daocloud.io/library/ubuntu:24.04

param(
    [string]$Version = "20.0.0",
    [string]$GatewayBase = "ubuntu:24.04"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Release = Join-Path $Root "release"
New-Item -ItemType Directory -Force $Release | Out-Null
$Tag = "hoshinoumi-gateway:${Version}"

Write-Host "==> 构建 gateway 镜像 $Tag" -ForegroundColor Cyan
docker build `
    -f gateway/Dockerfile.offline `
    --build-arg "BASE_IMAGE=$GatewayBase" `
    -t $Tag .
if ($LASTEXITCODE -ne 0) { throw "gateway 镜像构建失败" }

$Raw = Join-Path $Release ".gateway-image.tar"
$Out = Join-Path $Release "REC-v${Version}-gateway-docker.tar.gz"
docker save $Tag -o $Raw
if ($LASTEXITCODE -ne 0) { throw "docker save 失败" }

python -X utf8 -c "import gzip, shutil; shutil.copyfileobj(open(r'$Raw', 'rb'), gzip.open(r'$Out', 'wb'))"
Remove-Item $Raw -Force

Write-Host ""
Write-Host "[OK] $Out" -ForegroundColor Green
Write-Host ""
Write-Host "部署机："
Write-Host "  docker load -i REC-v${Version}-gateway-docker.tar.gz"
Write-Host "  docker run -d --name hoshinoumi-gateway --network host hoshinoumi-gateway:${Version}"
Write-Host ""
Write-Host "如果 bot API 不是 127.0.0.1:27004，先挂载 config/gateway.json 覆盖。"


