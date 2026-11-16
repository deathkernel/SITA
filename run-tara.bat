@echo off
setlocal
call "%~dp0run-sita.bat" %*
exit /b %errorlevel%
