# Crea dist\tk-iscrizioni-<ver>-windows.zip (aggiornamento) e dist\tk-iscrizioni-<ver>-portatile.zip (cartella da estrarre)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$version = (Select-String -Path 'tkiscrizioni\__init__.py' -Pattern 'VERSION = "(.+)"').Matches[0].Groups[1].Value
$stageRoot = Join-Path $env:TEMP 'tkiscrizioni-stage'
$stage = Join-Path $stageRoot 'app'
$dist = Join-Path $root 'dist'
$venv = Join-Path $root '.venv'

# Smart App Control blocca .venv\Scripts\python.exe (lanciatore non firmato): Python di base + librerie del venv,
# PYTHONPATH solo per la durata della chiamata (il collaudo del pacchetto non deve vedere le librerie del venv)
$venvPy = ((Get-Content (Join-Path $venv 'pyvenv.cfg') | Where-Object { $_ -match '^home\s*=' }) -replace '^home\s*=\s*', '').Trim() + '\python.exe'
function VenvPy { $env:PYTHONPATH = Join-Path $venv 'Lib\site-packages'; try { & $venvPy @args } finally { Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue } }
Write-Host "== tk-iscrizioni ${version}"
if (Test-Path $stageRoot) { Remove-Item $stageRoot -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null
New-Item -ItemType Directory -Force $dist | Out-Null

function Robo($src, $dst, [string[]]$extra) {
    & robocopy $src $dst /E /NFL /NDL /NJH /NJS /NP @extra | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy fallito ($LASTEXITCODE): $src" }
}

# icona
VenvPy tools_make_icon.py | Out-Null
if (-not (Test-Path 'assets\tk-iscrizioni.ico')) { throw 'Icona non generata' }

# Python ridotto (senza tkinter, test, pip...) + solo le parti di PySide6 che servono
$homeLine = Get-Content "$venv\pyvenv.cfg" | Where-Object { $_ -match '^home\s*=' }
$pyHome = ($homeLine -replace '^home\s*=\s*', '').Trim()
$py = Join-Path $stage 'python'
Robo $pyHome $py @('/XD', 'test', 'tests', 'idlelib', 'tkinter', 'turtledemo', 'tcl', 'include', 'libs', 'Scripts',
                   'ensurepip', 'lib2to3', 'site-packages', '__phello__', 'pydoc_data',
                   '/XF', '*.pdb', '_tkinter.pyd', 'tcl*.dll', 'tk*.dll', 'EXTERNALLY-MANAGED')
$sp = "$venv\Lib\site-packages"
$dsp = Join-Path $py 'Lib\site-packages'
New-Item -ItemType Directory -Force $dsp | Out-Null
Robo "$sp\shiboken6" "$dsp\shiboken6" @()
Robo "$sp\certifi" "$dsp\certifi" @()
$ps = "$sp\PySide6"
$dps = "$dsp\PySide6"
New-Item -ItemType Directory -Force $dps | Out-Null
$files = @('pyside6.abi3.dll', 'QtCore.pyd', 'QtGui.pyd', 'QtWidgets.pyd', 'Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll',
           'Qt6Svg.dll')
Get-ChildItem $ps -File | Where-Object {
    $_.Extension -eq '.py' -or $files -contains $_.Name -or $_.Name -match '^(msvcp140|vcruntime140|concrt140)'
} | ForEach-Object { Copy-Item $_.FullName $dps }
foreach ($plug in @('platforms\qwindows.dll', 'platforms\qoffscreen.dll', 'styles\qmodernwindowsstyle.dll',
                    'iconengines\qsvgicon.dll', 'imageformats\qjpeg.dll', 'imageformats\qico.dll', 'imageformats\qsvg.dll')) {
    $srcp = Join-Path "$ps\plugins" $plug
    if (Test-Path $srcp) {
        $dstp = Join-Path "$dps\plugins" $plug
        New-Item -ItemType Directory -Force (Split-Path $dstp) | Out-Null
        Copy-Item $srcp $dstp
    }
}
New-Item -ItemType Directory -Force "$dps\translations" | Out-Null
Copy-Item "$ps\translations\qtbase_it.qm" "$dps\translations\" -ErrorAction SilentlyContinue

Robo 'tkiscrizioni' "$stage\tkiscrizioni" @('/XD', '__pycache__')
New-Item -ItemType Directory -Force "$stage\assets" | Out-Null
Copy-Item 'assets\tk-iscrizioni.ico' "$stage\assets\"
Copy-Item 'run.py' $stage
# testi delle licenze (AGPL + componenti inclusi + COMPONENTI.txt) in app\licenze, accanto a run.py
VenvPy tools_licenze.py "$stage\licenze" windows | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Cartella licenze non preparata' }
foreach ($f in @('COPYING-AGPL-3.0.txt', 'COMPONENTI.txt', 'LGPL-3.0.txt', 'GPL-3.0.txt', 'MPL-2.0.txt', 'Python-PSF.txt')) {
    if (-not (Test-Path "$stage\licenze\$f")) { throw "Manca licenze\$f" }
}
& "$py\python.exe" -m compileall -q "$py\Lib" 2>$null | Out-Null
# il codice di tk-iscrizioni va nel pacchetto SOLO compilato: .pyc accanto ai moduli (-b), sorgenti tolti
& "$py\python.exe" -m compileall -q -b "$stage\tkiscrizioni" 2>$null | Out-Null
Get-ChildItem "$stage\tkiscrizioni" -Recurse -File -Filter '*.py' | Remove-Item -Force
Get-ChildItem "$stage\tkiscrizioni" -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
if (Get-ChildItem "$stage\tkiscrizioni" -Recurse -File -Filter '*.py') { throw 'Nel pacchetto sono rimasti dei sorgenti .py' }

# verifica 1: test del motore con il Python del pacchetto (finto server IMAP, cifratura DPAPI)
Robo 'tests' "$stage\tests" @('/XD', '__pycache__', '/XF', '*.png', '*.txt', '*.csv')
$env:PYTHONIOENCODING = 'utf-8'
$env:QT_QPA_FONTDIR = "$env:WINDIR\Fonts"  # PySide6 ridotto: senza, Qt scrive un avviso su stderr e PS5 lo prende per errore
$ErrorActionPreference = 'Continue'  # gli avvisi di Qt su stderr non sono errori
$out = & "$py\python.exe" "$stage\tests\test_core.py" 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "Test del motore falliti:`n$out" }
Write-Host "   test del motore OK"
$out = & "$py\python.exe" "$stage\tests\test_ui_scan.py" 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) { throw "Test dell'interfaccia falliti:`n$out" }
Write-Host "   test dell'interfaccia OK"
$ErrorActionPreference = 'Stop'
Remove-Item "$stage\tests" -Recurse -Force
Remove-Item "$py\python.exe"

# verifica 2: avvio reale dal runtime ridotto (finestra con dati di esempio + esportazione)
$shot = Join-Path $stageRoot 'selftest.png'
$p = Start-Process "$py\pythonw.exe" -ArgumentList "`"$stage\run.py`"", '--selftest', "`"$shot`"" -PassThru
if (-not $p.WaitForExit(60000)) { Stop-Process -Id $p.Id -Force; throw 'Selftest in timeout' }
if (-not (Test-Path $shot) -or -not (Test-Path "$stageRoot\selftest.csv")) { throw 'Selftest fallito: il pacchetto non avvia tk-iscrizioni' }
Copy-Item $shot (Join-Path $dist "selftest-$version.png") -Force
Remove-Item $shot, "$stageRoot\selftest.csv"
Write-Host "   selftest del pacchetto OK (finestra + esportazione)"
Get-ChildItem $stage -Recurse -Directory -Filter 'Dati' | Remove-Item -Recurse -Force

$zipCode = "import os,sys,zipfile`nsrc,dst=sys.argv[1],sys.argv[2]`nwith zipfile.ZipFile(dst,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:`n  for d,_,fs in os.walk(src):`n    for f in fs:`n      p=os.path.join(d,f); z.write(p, os.path.relpath(p,src).replace(os.sep,'/'))"
$updateZip = Join-Path $dist "tk-iscrizioni-$version-windows.zip"
& "$pyHome\python.exe" -c $zipCode $stage $updateZip
if ($LASTEXITCODE -ne 0) { throw 'ZIP aggiornamento fallito' }
# controllo dello ZIP: licenze e librerie comuni (software libero) dentro il pacchetto
$checkCode = "import sys,zipfile`nn=set(zipfile.ZipFile(sys.argv[1]).namelist())`nneed=['licenze/COPYING-AGPL-3.0.txt','licenze/COMPONENTI.txt','tkiscrizioni/tk_licenza.pyc','tkiscrizioni/tk_licenza_qt.pyc','tkiscrizioni/tk_aggiornamento.pyc','tkiscrizioni/disiscrizione.pyc','run.py']`nmiss=[x for x in need if x not in n]`nprint('mancano: '+', '.join(miss)) if miss else None`nsys.exit(1 if miss else 0)"
& "$pyHome\python.exe" -c $checkCode $updateZip
if ($LASTEXITCODE -ne 0) { throw 'Nello ZIP mancano dei file (licenze o librerie)' }

$pack = Join-Path $stageRoot "pack\tk-iscrizioni-$version"
New-Item -ItemType Directory -Force "$pack\Dati" | Out-Null
Set-Content -Path "$pack\Dati\.tieni" -Value '' -Encoding ASCII
Robo $stage "$pack\app" @()
$cmd = Get-Content "$PSScriptRoot\Avvia tk-iscrizioni.cmd" -Raw
[IO.File]::WriteAllText("$pack\Avvia tk-iscrizioni.cmd", ($cmd -replace "`r?`n", "`r`n"), [Text.Encoding]::ASCII)
$readme = Get-Content "$PSScriptRoot\Leggimi.txt" -Raw -Encoding UTF8
[IO.File]::WriteAllText("$pack\Leggimi.txt", ($readme -replace "`r?`n", "`r`n"), (New-Object Text.UTF8Encoding($true)))
$portZip = Join-Path $dist "tk-iscrizioni-$version-portatile.zip"
& "$pyHome\python.exe" -c $zipCode (Join-Path $stageRoot 'pack') $portZip
if ($LASTEXITCODE -ne 0) { throw 'ZIP portatile fallito' }
# --- installer exe (stesso modello di tk-pdf: setup.cs = strumenti\tk-setup.cs); contiene il pacchetto di aggiornamento
$csc = "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
$sizeKb = [int]((Get-ChildItem $stage -Recurse -File | Measure-Object Length -Sum).Sum / 1KB)
$map = [ordered]@{
    NAME = 'tk-iscrizioni'
    SLUG = 'tk-iscrizioni'
    TAGLINE = 'a cosa sei iscritto con la tua email'
    SUBDIR = 'app'
    DATADIR = 'Dati'
    ICON = 'tk-iscrizioni.ico'
    ACCENT = '#7C3AED'
    UNINSTALL = 'cmd'
    UNINSTALLKEY = 'tk-iscrizioni'
    LNK = 'tk-iscrizioni'
    LEGACYLNK = 'tkISCRIZIONI'
    LAUNCHSCHEMA = ''
    ITEMS = ''
    # licenza.json (consenso statistiche, inviti) e la cartella di riserva se «Dati» non era scrivibile
    EXTRADATA = '%APPDATA%\tk-iscrizioni;%USERPROFILE%\Documents\tkISCRIZIONI'
    VERSION = $version
    SIZEKB = "$sizeKb"
}
$setupSrc = Get-Content "$PSScriptRoot\setup.cs" -Raw -Encoding UTF8
foreach ($k in $map.Keys) { $setupSrc = $setupSrc.Replace("@@$k@@", [string]$map[$k]) }
$genSrc = Join-Path $stageRoot 'setup.cs'
[IO.File]::WriteAllText($genSrc, $setupSrc, (New-Object Text.UTF8Encoding($true)))
$setupExe = Join-Path $dist "tk-iscrizioni-setup-$version.exe"
& $csc /nologo /optimize+ /target:winexe /platform:anycpu /win32icon:"$root\assets\tk-iscrizioni.ico" `
    /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Core.dll `
    /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll `
    /resource:"$updateZip",payload.zip /out:"$setupExe" $genSrc
if ($LASTEXITCODE -ne 0) { throw 'Compilazione installer fallita' }
Write-Host "   installer: $setupExe ($([math]::Round((Get-Item $setupExe).Length/1MB,1)) MB)"

$sha = (Get-FileHash $updateZip -Algorithm SHA256).Hash.ToLower()
Write-Host "== Creati:`n   $portZip ($([math]::Round((Get-Item $portZip).Length/1MB,1)) MB)`n   $updateZip`n   sha256 aggiornamento: $sha"
Remove-Item $stageRoot -Recurse -Force
