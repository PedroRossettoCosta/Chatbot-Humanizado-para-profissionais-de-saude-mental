@echo off
rem Sobe a MarIA para desenvolvimento no Windows: banco, API e painel.
rem Precisa do Docker Desktop aberto. Cada servidor abre na sua janela;
rem para parar, feche as janelas (ou Ctrl+C em cada uma).
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] Banco de dados (Docker)...
docker compose up -d postgres
if errorlevel 1 (
  echo.
  echo Nao consegui subir o banco. O Docker Desktop esta aberto?
  pause
  exit /b 1
)

echo [2/4] Encerrando servidores antigos nas portas 8000 e 5173...
rem O --reload do uvicorn as vezes deixa um processo antigo preso na
rem porta 8000, servindo codigo velho. Melhor comecar do zero.
for %%P in (8000 5173) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do taskkill /PID %%I /F >nul 2>&1
)

echo [3/4] API (http://127.0.0.1:8000)...
start "MarIA - API" cmd /k "cd /d backend && .venv\Scripts\python.exe -m alembic upgrade head && .venv\Scripts\python.exe -m uvicorn app.main:app --reload"

echo [4/4] Painel (http://localhost:5173)...
start "MarIA - Painel" cmd /k "cd /d frontend && npm run dev"

rem Espera os dois subirem antes de abrir o navegador.
timeout /t 8 /nobreak >nul
rem ?sair encerra a sessao salva no navegador: o teste comeca pelo login.
start "" "http://localhost:5173/?sair"
