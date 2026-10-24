# Abre una consola REAL, corre la compuerta con la v3 y captura la ventana.
#
#     powershell -ExecutionPolicy Bypass -File scripts\capturar_compuerta.ps1
#
# La consigna pide «captura de la compuerta con la v3 en codigo 0». Una imagen
# dibujada a partir del texto no seria una captura: esto fotografia la ventana
# de la consola tal como la veria cualquiera que ejecute el comando.
param(
    [string]$Entrega = "$PSScriptRoot\..\docs\M7_Evals_BIOMED",
    [string]$Python  = "$PSScriptRoot\..\backend-clinic\.venv\Scripts\python.exe",
    [string]$Salida  = "$PSScriptRoot\..\docs\M7_Evals_BIOMED\evidencia\compuerta_v3.png"
)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Ventana {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr h, int x, int y, int w, int hh, bool rep);
}
"@

$Entrega = (Resolve-Path $Entrega).Path
$Python  = (Resolve-Path $Python).Path
$orden = "`$host.UI.RawUI.WindowTitle = 'M7 Evals BIOMED - compuerta v3'; " +
         "Set-Location '$Entrega'; `$env:PYTHONIOENCODING='utf-8'; " +
         "Write-Host 'PS> python evals\evaluar.py correr v3' -ForegroundColor Yellow; " +
         "& '$Python' evals\evaluar.py correr v3; " +
         "Write-Host ('PS> `$LASTEXITCODE  ->  ' + `$LASTEXITCODE) -ForegroundColor Green"
$p = Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-Command', $orden -PassThru
Start-Sleep -Seconds 6
$p.Refresh()
$h = $p.MainWindowHandle
if ($h -eq [IntPtr]::Zero) { throw 'no se encontro la ventana de la consola' }
[Ventana]::MoveWindow($h, 40, 40, 1000, 780, $true) | Out-Null
[Ventana]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Seconds 2
$r = New-Object Ventana+RECT
[Ventana]::GetWindowRect($h, [ref]$r) | Out-Null
$ancho = $r.R - $r.L; $alto = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $ancho, $alto
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$bmp.Save($Salida, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Stop-Process -Id $p.Id
Write-Output "captura: $Salida ($ancho x $alto)"
