@echo off
setlocal
cd /d "%~dp0"
python -u nao_run.py %*
