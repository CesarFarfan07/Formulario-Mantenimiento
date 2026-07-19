@echo off
echo Sincronizando PostgreSQL a SQLite...
cd /d "%~dp0"
python sync_to_sqlite.py
if %errorlevel% equ 0 (
    echo OK - SQLite actualizado.
) else (
    echo ERROR - Revisa el mensaje de arriba.
)
pause
