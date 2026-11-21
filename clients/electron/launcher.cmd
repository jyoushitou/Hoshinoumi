@echo off
set ELECTRON_RUN_AS_NODE=
start "" "%~dp0Hoshinoumi.exe" --no-sandbox --disable-gpu --disable-crash-reporter --disable-breakpad "--user-data-dir=%~dp0user-data"
