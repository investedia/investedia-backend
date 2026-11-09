@echo off
powershell.exe -NoProfile -File "%~dp0scripts\maven.ps1" %*
exit /b %errorlevel%
