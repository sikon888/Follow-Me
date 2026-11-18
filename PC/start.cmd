@echo off
setlocal
cd /d "%~dp0"
set "HOST=0.0.0.0"
set "FOLLOW_ME_PYTHON=.venv\Scripts\python.exe"
set "FOLLOW_ME_VERSION_CHECK=import sys, struct; sys.exit(sys.version_info[:2] != (3, 14) or struct.calcsize('P') != 8)"

"%FOLLOW_ME_PYTHON%" -c "%FOLLOW_ME_VERSION_CHECK%" >nul 2>&1
if not errorlevel 1 goto dependencies

py -3.14 -c "%FOLLOW_ME_VERSION_CHECK%" >nul 2>&1
if not errorlevel 1 (
    py -3.14 -m venv .venv
) else (
    python -c "%FOLLOW_ME_VERSION_CHECK%" >nul 2>&1
    if errorlevel 1 (
        echo Install Python 3.14 x64 and enable its launcher or PATH option.
        goto failed
    )
    python -m venv .venv
)
if errorlevel 1 goto failed

:dependencies
"%FOLLOW_ME_PYTHON%" -c "from pathlib import Path; import hashlib, sys; marker = Path('.venv/follow-me-requirements'); expected = str(Path.cwd()) + '\n' + hashlib.sha256(Path('requirements.txt').read_bytes()).hexdigest(); sys.exit(not marker.is_file() or marker.read_text(encoding='utf-8') != expected)" >nul 2>&1
if not errorlevel 1 goto server

if exist "wheelhouse\*.whl" (
    "%FOLLOW_ME_PYTHON%" -m pip install --disable-pip-version-check --no-index --find-links wheelhouse -r requirements.txt
) else (
    "%FOLLOW_ME_PYTHON%" -m pip install --disable-pip-version-check -r requirements.txt
)
if errorlevel 1 goto failed
"%FOLLOW_ME_PYTHON%" -c "from pathlib import Path; import hashlib; Path('.venv/follow-me-requirements').write_text(str(Path.cwd()) + '\n' + hashlib.sha256(Path('requirements.txt').read_bytes()).hexdigest(), encoding='utf-8')"
if errorlevel 1 goto failed

:server
echo Open http://127.0.0.1:5001 on this PC.
echo For the Pi, use ipconfig to find this PC's Ethernet or Wi-Fi IPv4 address.
"%FOLLOW_ME_PYTHON%" app.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo Follow Me could not start. See the error above.
pause
exit /b 1
