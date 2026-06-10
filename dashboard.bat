@echo off
REM ===================================================================
REM פותח את לוח הבקרה של סוכן המניות בדפדפן.
REM קיצור דרך לקובץ הזה נמצא על שולחן העבודה.
REM ===================================================================
chcp 65001 >nul
cd /d "C:\claude\stock-agent"
echo פותח את לוח הבקרה בדפדפן... (לסגירה: סגור חלון זה)
"C:\Users\Almog\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run dashboard\app.py
pause
