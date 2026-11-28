@echo off
rem Bam dup de chay: mo 2 cua so terminal (service FastAPI + Streamlit) va mo trinh duyet.
rem Dong cua so terminal tuong ung de tat tung phan. Huong dan day du: run.md
setlocal
cd /d "%~dp0"

rem Cong service phai khop OCR_SERVICE_URL trong .env (mac dinh http://127.0.0.1:8000)
set "SERVICE_PORT=8000"
set "UI_PORT=8501"
set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [Loi] Chua co .venv. Xem muc "Cai dat lan dau" trong run.md.
    pause
    exit /b 1
)
if not exist ".env" (
    echo [Loi] Chua co file .env. Sao chep .env.example thanh .env roi dien key.
    pause
    exit /b 1
)

rem Chay qua tools\run-with-ansi-colors.py: console Windows 10 mac dinh khong hien mau ANSI
rem (in ra ky tu la), script nay bat che do mau truoc khi chay uvicorn / streamlit
set "RUN=%~dp0tools\run-with-ansi-colors.py"

start "OCR service :%SERVICE_PORT%" cmd /k ""%PY%" "%RUN%" uvicorn ocr_baseline.api.app:create_app --factory --port %SERVICE_PORT%"

rem Doi service khoi dong truoc khi mo Streamlit
timeout /t 4 /nobreak >nul

rem --server.headless true: bo cau hoi email lan dau cua Streamlit, trinh duyet duoc mo o duoi
rem --server.address 127.0.0.1: chi mo tren may nay, khong lo ra mang LAN / Internet
start "OCR Streamlit :%UI_PORT%" cmd /k ""%PY%" "%RUN%" streamlit run app.py --server.port %UI_PORT% --server.address 127.0.0.1 --server.headless true"

timeout /t 4 /nobreak >nul
start "" "http://localhost:%UI_PORT%"

endlocal
