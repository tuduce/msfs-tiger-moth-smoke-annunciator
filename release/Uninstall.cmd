@echo off
cd /d "%~dp0"
where py >nul 2>nul && (py -3 install_annunciator.py --uninstall %* & goto done)
where python >nul 2>nul && (python install_annunciator.py --uninstall %* & goto done)
echo Python 3 was not found.
:done
echo.
pause
