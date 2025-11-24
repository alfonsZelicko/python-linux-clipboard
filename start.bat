@echo off
REM Spustí CMD, aktivuje virtuální prostředí a spustí script

REM Aktivace virtuálního prostředí
call venv\Scripts\activate

REM Spuštění scriptu
python linux-clipboard.py

REM Volitelně: počkej na klávesu, než se okno zavře
pause