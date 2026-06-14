@echo off
REM ===================================================================
REM Wrapper for the daily scheduled run of the stock agent.
REM Registered in Windows Task Scheduler as task "StockAgentDaily".
REM Appends each run's output (with timestamps) to data\daily_run.log.
REM ===================================================================

REM Use UTF-8 so the Hebrew output is logged correctly.
chcp 65001 >nul

REM Always run from the project directory.
cd /d "C:\claude\stock-agent"

echo.>> "data\daily_run.log"
echo ============================================================>> "data\daily_run.log"
echo ===== Run started: %DATE% %TIME% =====>> "data\daily_run.log"

REM Full path to Python so the task doesn't depend on PATH.
set PY="C:\Users\Almog\AppData\Local\Programs\Python\Python312\python.exe"

REM 1) Watchlist run (scores, portfolio, alerts, email).
%PY% run.py >> "data\daily_run.log" 2>&1

REM 2) Market-wide universe scan (S&P 500 + Nasdaq-100 discovery engine, ~1.5 min).
%PY% scanner.py ALL >> "data\daily_run.log" 2>&1

echo ===== Run finished: %DATE% %TIME% =====>> "data\daily_run.log"
