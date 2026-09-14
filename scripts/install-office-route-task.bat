@echo off
REM Instalador de la tarea automatica que mantiene el acceso a la red
REM interna de la oficina mientras la VPN esta conectada.
REM
REM COMO USAR: click derecho sobre este archivo -> "Ejecutar como
REM administrador". Se corre UNA SOLA VEZ. Despues de eso queda
REM funcionando solo: revisa la conexion cada 2 minutos, incluso despues
REM de reiniciar la computadora. No hay que volver a tocar nada.

set TASK_NAME=BinauralOfficeRoute
set SCRIPT_DIR=%~dp0
set SCRIPT_PATH=%SCRIPT_DIR%fix-office-route.ps1

echo Instalando tarea programada "%TASK_NAME%"...
schtasks /create /tn "%TASK_NAME%" /tr "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File \"%SCRIPT_PATH%\"" /sc MINUTE /mo 2 /rl HIGHEST /f

if %errorlevel%==0 (
    echo.
    echo Listo. Quedo instalada y va a revisar la conexion cada 2 minutos
    echo de forma automatica, incluso despues de reiniciar la computadora.
    echo No hace falta hacer nada mas - ya podes cerrar esta ventana.
) else (
    echo.
    echo Algo fallo. Asegurate de haber abierto este archivo con
    echo "Ejecutar como administrador" ^(click derecho sobre el .bat,
    echo luego "Ejecutar como administrador"^), y volve a intentar.
)

echo.
pause
