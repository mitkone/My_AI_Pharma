@echo off
cd /d "%~dp0"
echo Starting Pharma Data Viz...
echo Wait 10-15 sec for data load.
echo.
echo On this laptop:  http://127.0.0.1:8501
echo From other devices (same WiFi):  http://YOUR_IP:8501
echo    Find your IP: ipconfig ^| findstr "IPv4"
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python and add to PATH.
    pause
    exit /b 1
)
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
if errorlevel 1 (
    echo.
    echo ERROR: Streamlit failed. Try: pip install -r requirements.txt
)
pause
