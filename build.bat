@echo off
title MultiDmall - Build EXE
echo Installation de PyInstaller...
pip install pyinstaller discord.py colorama
echo.
echo Build en cours...
pyinstaller --onefile --name MultiDmall --icon=NONE --add-data "config.json;." main.py
echo.
echo ✅ EXE genere dans le dossier dist\
pause
