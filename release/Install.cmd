@echo off
rem Double-click to install the Tiger Moth Smoke Annunciator. Needs Python 3 (https://www.python.org/downloads/).
cd /d "%~dp0"
where py >nul 2>nul && (py -3 install_annunciator.py %* & goto done)
where python >nul 2>nul && (python install_annunciator.py %* & goto done)
echo Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again.
:done
echo.
pause
