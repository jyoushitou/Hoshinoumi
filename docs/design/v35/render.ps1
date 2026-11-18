$ErrorActionPreference = "Stop"
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$items = @(
  @("web", "chat.html", "chat.png", 1440, 900),
  @("web", "command.html", "command.png", 1440, 900),
  @("web", "savings.html", "savings.png", 1440, 900),
  @("web", "info.html", "info.png", 1440, 900),
  @("web", "plugins.html", "plugins.png", 1440, 900),
  @("web", "persona.html", "persona.png", 1440, 900),
  @("qt", "chat.html", "chat.png", 1440, 900),
  @("android", "chat.html", "chat.png", 390, 844),
  @("android", "savings.html", "savings.png", 390, 844),
  @("android", "settings.html", "settings.png", 390, 844),
  @("emui", "chat.html", "chat.png", 390, 844),
  @("emui", "settings.html", "settings.png", 390, 844),
  @("emui", "privacy.html", "privacy.png", 390, 844),
  @("dsh", "chat.html", "chat.png", 1440, 900),
  @("dsh", "plugin.html", "plugin.png", 1440, 900)

)

foreach ($it in $items) {
  $folder = Join-Path $root $it[0]
  $src = Join-Path $folder $it[1]
  $out = Join-Path $folder $it[2]
  $tmp = Join-Path $folder ("_" + $it[2])
  $w = $it[3]; $h = $it[4]
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
  Write-Host "rendered $($it[0])/$($it[2])"
}
