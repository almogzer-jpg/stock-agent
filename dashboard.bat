@echo off
REM Stock Agent launcher - opens the dashboard in the browser.
chcp 65001 >nul
cd /d "C:\claude\stock-agent"
echo Starting Stock Agent server...
start "StockAgent Server" /min "C:\Users\Almog\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run dashboard\app.py --server.port 8501
echo Waiting for the server...
ping -n 9 127.0.0.1 >nul
start "" http://localhost:8501
echo Browser opened. You can close this window.
ping -n 4 127.0.0.1 >nul
