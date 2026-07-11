# Registra el asistente para que arranque al iniciar sesión en Windows.
#
# Task Scheduler y NO la carpeta Startup (ADR del ROADMAP): el Task Scheduler lo
# RELANZA si el proceso crashea. La carpeta Startup solo lo lanza una vez y si muere,
# muere. Para un asistente always-on esa diferencia lo es todo.
#
# NO requiere privilegios de administrador (regla del proyecto: nunca correr elevados).
#
# Uso:      .\scripts\install_autostart.ps1
# Quitarlo: Unregister-ScheduledTask -TaskName "AsistenteVirtual" -Confirm:$false

$ErrorActionPreference = "Stop"

$raiz    = Split-Path -Parent $PSScriptRoot
$python  = Join-Path $raiz ".venv\Scripts\pythonw.exe"   # pythonw: sin ventana de consola
$script  = Join-Path $raiz "main.py"
$tarea   = "AsistenteVirtual"

if (-not (Test-Path $python)) {
    throw "No encuentro $python. Creá el venv primero: py -3.11 -m venv .venv"
}

$accion = New-ScheduledTaskAction -Execute $python -Argument "`"$script`" --daemon" -WorkingDirectory $raiz
$disparador = New-ScheduledTaskTrigger -AtLogOn

# RestartCount: si el proceso muere, Windows lo vuelve a levantar. Esta es la razón de
# usar Task Scheduler en lugar de la carpeta Startup.
$opciones = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0)   # sin límite: es un servicio

Register-ScheduledTask -TaskName $tarea -Action $accion -Trigger $disparador `
    -Settings $opciones -Description "Asistente virtual local (modo residente)" -Force | Out-Null

Write-Host "Listo. '$tarea' arrancará al iniciar sesión." -ForegroundColor Green
Write-Host "Probalo ya:  Start-ScheduledTask -TaskName $tarea"
Write-Host "Quitarlo:    Unregister-ScheduledTask -TaskName $tarea -Confirm:`$false"
