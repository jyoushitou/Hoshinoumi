$ErrorActionPreference = "Stop"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$screens = Join-Path $root "screens"
New-Item -ItemType Directory -Force $screens | Out-Null

$items = @(
  @("web-chat.html", "web-chat.png", 1440, 900),
  @("web-command.html", "web-command.png", 1440, 900),
  @("web-savings.html", "web-savings.png", 1440, 900),
  @("web-info.html", "web-info.png", 1440, 900),
  @("web-plugins.html", "web-plugins.png", 1440, 900),
  @("web-persona.html", "web-persona.png", 1440, 900),
  @("qt-desktop.html", "qt-desktop.png", 1440, 900),
  @("android-chat.html", "android-chat.png", 390, 844),
  @("android-savings.html", "android-savings.png", 390, 844),
  @("android-settings.html", "android-settings.png", 390, 844),
  @("emui-chat.html", "emui-chat.png", 390, 844),
  @("emui-settings.html", "emui-settings.png", 390, 844),
  @("emui-privacy.html", "emui-privacy.png", 390, 844)
)

foreach ($it in $items) {
  $src = Join-Path $root $it[0]
  $out = Join-Path $screens $it[1]
  $tmp = Join-Path $screens ("_" + $it[1])
  $w = $it[2]; $h = $it[3]
  $profile = Join-Path $env:TEMP ("chrome-design-" + [guid]::NewGuid().ToString("N"))
  Remove-Item $tmp, $out -ErrorAction SilentlyContinue
  & $chrome --headless=new --disable-gpu --hide-scrollbars --no-first-run `
    --user-data-dir=$profile --force-device-scale-factor=1 `
    --window-size=$w,($h + 90) --virtual-time-budget=1200 `
    --screenshot=$tmp ("file:///" + $src.Replace("\", "/"))
  for ($i = 0; $i -lt 40 -and -not (Test-Path $tmp); $i++) { Start-Sleep -Milliseconds 200 }
  if (-not (Test-Path $tmp)) { throw "screenshot failed: $($it[1])" }
  python -c "from PIL import Image; im=Image.open(r'$tmp'); im.crop((0,0,$w,$h)).save(r'$out')"
  Remove-Item $tmp -ErrorAction SilentlyContinue
  Write-Host "rendered $($it[1])"
}
