@echo off
rem Avvia tk-iscrizioni (nessuna installazione). Archivio e impostazioni stanno nella cartella "Dati".
start "" "%~dp0app\python\pythonw.exe" "%~dp0app\run.py" %*
