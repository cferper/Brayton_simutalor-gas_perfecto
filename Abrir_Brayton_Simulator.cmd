@echo off
setlocal
cd /d "%~dp0"
title Brayton Simulator - Formulario local

rem Reutilizar el formulario si ya esta funcionando en el puerto habitual.
powershell.exe -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5001/' -TimeoutSec 2; if ($r.Content -match '<form' -and $r.Content -match 'relacion_presiones') { exit 0 } } catch {}; exit 1" >nul 2>&1
if errorlevel 1 goto iniciar
start "" "http://127.0.0.1:5001/"
exit /b 0

:iniciar
if not exist ".venv\Scripts\python.exe" (
    echo No se encuentra el entorno .venv del proyecto. Consulta README.md.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -B -c "import flask, numpy, matplotlib"
if errorlevel 1 (
    echo Faltan dependencias. Instala requirements.txt en .venv.
    pause
    exit /b 1
)

rem Esperar a que responda el formulario antes de abrir el navegador.
start "" powershell.exe -NoProfile -WindowStyle Hidden -Command "for ($i = 0; $i -lt 30; $i++) { try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5001/' -TimeoutSec 1; if ($r.Content -match '<form' -and $r.Content -match 'relacion_presiones') { Start-Process 'http://127.0.0.1:5001/'; exit 0 } } catch {}; Start-Sleep -Seconds 1 }; exit 1"
echo El formulario se abrira en el navegador cuando el servidor este listo.
echo Manten esta ventana abierta. Para detener el servidor, pulsa Ctrl+C.
echo.
".venv\Scripts\python.exe" -B web_app.py
if errorlevel 1 (
    echo No se ha podido mantener el servidor. Revisa el error mostrado arriba.
    echo Si el puerto 5001 esta ocupado por otra aplicacion, liberalo y vuelve a intentarlo.
    pause
    exit /b 1
)
