@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SITA - Local AI Workspace

rem Enable ANSI colors on modern Windows terminals; keep plain-text fallback.
set "ESC="
for /F "delims=" %%A in ('echo prompt $E^| cmd') do set "ESC=%%A"
if defined ESC (
  set "GOLD=%ESC%[38;5;220m"
  set "CYAN=%ESC%[38;5;81m"
  set "GREEN=%ESC%[92m"
  set "YELLOW=%ESC%[93m"
  set "RED=%ESC%[91m"
  set "DIM=%ESC%[90m"
  set "RESET=%ESC%[0m"
) else (
  set "GOLD="
  set "CYAN="
  set "GREEN="
  set "YELLOW="
  set "RED="
  set "DIM="
  set "RESET="
)

cls
echo.
echo   +------------------------------------------------------------------------+
echo   ^| %DIM%Welcome to%RESET% %CYAN%SITA%RESET%                                                           ^|
echo   ^|                                                                        ^|
echo   ^|         %GOLD%##########    ##########    ##########      ######  %RESET%                   ^|
echo   ^|         %GOLD%##                ##            ##        ##      ##%RESET%                   ^|
echo   ^|         %GOLD%##                ##            ##        ##      ##%RESET%                   ^|
echo   ^|         %GOLD%##########        ##            ##        ##########%RESET%                   ^|
echo   ^|         %GOLD%        ##        ##            ##        ##      ##%RESET%                   ^|
echo   ^|         %GOLD%        ##        ##            ##        ##      ##%RESET%                   ^|
echo   ^|         %GOLD%##########    ##########        ##        ##      ##%RESET%                   ^|
echo   ^|                                                                        ^|
echo   ^|                         %CYAN%LOCAL AI WORKSPACE%RESET%                             ^|
echo   ^|   %DIM%Private by design. Local-first by default.%RESET%                            ^|
echo   +------------------------------------------------------------------------+
echo.

call :section "Checking project integrity"
rem Check tracked project files only; recursive findstr can scan .venv and match separator text.
git grep -n -I -E "^(<<<<<<<|=======|>>>>>>>)" -- pyproject.toml src tests >nul 2>nul
if not errorlevel 1 (
  call :error "Unresolved Git conflict markers were found in tracked project files."
  git grep -n -I -E "^(<<<<<<<|=======|>>>>>>>)" -- pyproject.toml src tests
  echo Resolve every conflict, save the files, and run run-sita.bat again.
  exit /b 1
)
if errorlevel 2 (
  call :error "Could not inspect tracked project files for merge-conflict markers."
  echo Verify that Git is installed and this folder is a valid Git repository.
  exit /b 1
)
call :success "Project integrity check passed."

call :section "Preparing Python environment"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 (
    call :error "Could not create the SITA virtual environment. Install Python 3.11 or newer first."
    exit /b 1
  )
)
call :info "Installing SITA core package..."
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
  call :error "SITA installation failed."
  exit /b 1
)
call :success "SITA core package is ready."

".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info < (3, 15) else 1)"
if errorlevel 1 (
  call :warning "Skipping optional Voice transcription dependencies on Python 3.15 or newer."
) else (
  call :info "Installing optional Voice transcription dependencies..."
  ".venv\Scripts\python.exe" -m pip install -e ".[voice]"
  if errorlevel 1 (
    call :warning "Voice transcription dependencies are unavailable; the rest of SITA will continue."
  ) else (
    call :success "Voice transcription dependencies are ready."
  )
)

call :section "Building SITA interface"
rem Build the premium React workspace when Node.js is available.
rem The Python app retains its static UI fallback if the optional build cannot run.
if exist "frontend\package.json" (
  where npm >nul 2>nul
  if errorlevel 1 (
    call :warning "Node.js/npm is unavailable; SITA will use the bundled static UI fallback."
  ) else (
    pushd frontend
    if not exist "node_modules\vite\bin\vite.js" (
      call :info "Installing frontend packages..."
      call npm install --no-audit --no-fund
    )
    if not errorlevel 1 (
      call :info "Compiling React production interface..."
      call npm run build
    )
    if errorlevel 1 (
      call :warning "React workspace build failed; SITA will use the static UI fallback when no compiled build exists."
    ) else (
      call :success "Frontend build completed."
    )
    popd
  )
)

if not exist "sita.toml" (
  if exist "sita.toml" (
    copy "sita.toml" "sita.toml" >nul
  ) else (
    copy "sita.example.toml" "sita.toml" >nul
  )
)

call :section "Preparing native Handler"
".venv\Scripts\python.exe" -m tara_app.handler_launcher prepare
if errorlevel 1 (
  call :warning "Native Handler preparation returned a non-zero status."
)

call :section "Launching SITA"
call :success "Startup checks complete. Opening your local workspace..."
echo.
".venv\Scripts\python.exe" -m tara_app --config "sita.toml"
set "SITA_EXIT_CODE=%errorlevel%"
if not "%SITA_EXIT_CODE%"=="0" call :error "SITA exited with code %SITA_EXIT_CODE%."
if "%SITA_EXIT_CODE%"=="0" call :success "SITA shut down cleanly."
echo.
endlocal & exit /b %SITA_EXIT_CODE%

:section
echo.
echo %CYAN%  [ %~1 ]%RESET%
echo %DIM%  ------------------------------------------------------------%RESET%
exit /b 0

:info
echo %CYAN%  [INFO] %~1%RESET%
exit /b 0

:success
echo %GREEN%  [ OK ] %~1%RESET%
exit /b 0

:warning
echo %YELLOW%  [WARN] %~1%RESET%
exit /b 0

:error
echo %RED%  [FAIL] %~1%RESET%
exit /b 0
