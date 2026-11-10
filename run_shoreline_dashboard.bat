@echo off
setlocal
cd /d "%~dp0"

echo Shoreline Remediation Decision Support
 echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON=py -3.11"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo Python 3.11 was not found. Please install Python 3.11 and try again.
        pause
        exit /b 1
    )
    set "PYTHON=python"
)

echo Checking required packages...
%PYTHON% -c "import streamlit, numpy, pandas, sklearn, scipy, matplotlib, xgboost" >nul 2>&1
if errorlevel 1 (
    echo Installing missing packages from requirements.txt...
    %PYTHON% -m pip install -r requirements.txt
    if errorlevel 1 (
        echo Package installation failed.
        pause
        exit /b 1
    )
)

echo Starting the dashboard...
%PYTHON% -m streamlit run src\shoreline_remediation\dashboard.py --server.headless false
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Dashboard exited with code %EXIT_CODE%.
    pause
    exit /b %EXIT_CODE%
)

endlocal
exit /b 0
