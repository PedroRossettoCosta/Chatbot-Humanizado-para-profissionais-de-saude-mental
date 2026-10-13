@echo off
rem Sobe a SelenIA para desenvolvimento no Windows: banco, API e painel.
rem Serve para qualquer maquina: na primeira vez instala o que falta
rem (venv, pacotes, .env); nas seguintes so confere e sobe tudo. Abre o
rem Docker Desktop sozinho se ele estiver fechado. Cada servidor abre na
rem sua janela; para parar, feche as janelas (ou Ctrl+C em cada uma).
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [1/8] Conferindo os programas necessarios...
set "FALTA="
where docker >nul 2>&1 || (echo     Falta o Docker Desktop: https://www.docker.com/products/docker-desktop/ & set "FALTA=1")
where npm >nul 2>&1 || (echo     Falta o Node.js 18+: https://nodejs.org/ & set "FALTA=1")
if not exist "backend\.venv\Scripts\python.exe" call :acha_python
if defined FALTA (
  echo.
  echo Instale o que falta, feche e abra este script de novo.
  pause
  exit /b 1
)

echo [2/8] Docker...
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
echo     Docker Desktop fechado: abrindo e esperando ele ficar pronto...
rem O instalador pode colocar o Docker Desktop para todos os usuarios
rem ou so para o usuario atual; tenta os dois lugares.
if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
  start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
) else if exist "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe" (
  start "" "%LOCALAPPDATA%\Programs\DockerDesktop\Docker Desktop.exe"
) else (
  echo     Nao achei o Docker Desktop instalado. Abra-o pelo menu Iniciar.
)
set /a TENTATIVAS=0
:espera_docker
ping -n 4 127.0.0.1 >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_ok
set /a TENTATIVAS+=1
if %TENTATIVAS% lss 60 goto espera_docker
echo.
echo O Docker nao respondeu em 3 minutos. Abra o Docker Desktop, espere
echo ele terminar de carregar e rode este script de novo.
pause
exit /b 1
:docker_ok

echo [3/8] Banco de dados (PostgreSQL no Docker)...
docker compose up -d postgres
if errorlevel 1 (
  echo.
  echo Nao consegui subir o banco. Veja a mensagem acima.
  pause
  exit /b 1
)
rem Na primeira vez o Postgres leva alguns segundos para criar o banco;
rem as migracoes so podem rodar depois disso. Pela rede (-h) ele so
rem responde quando a inicializacao terminou de verdade.
set /a TENTATIVAS=0
:espera_banco
docker compose exec -T postgres pg_isready -h 127.0.0.1 -U postgres -d chatbot_tcc >nul 2>&1
if not errorlevel 1 goto banco_ok
set /a TENTATIVAS+=1
if %TENTATIVAS% geq 30 (
  echo     O banco nao ficou pronto em 60 segundos. Veja: docker compose logs postgres
  pause
  exit /b 1
)
ping -n 3 127.0.0.1 >nul
goto espera_banco
:banco_ok

echo [4/8] Backend: ambiente Python e pacotes...
if not exist "backend\.venv\Scripts\python.exe" (
  echo     Criando o ambiente virtual [so na primeira vez]...
  %PY% -m venv backend\.venv || goto erro_instalacao
)
rem Reinstala so quando o requirements.txt mudou desde a ultima vez
rem (ex.: depois de um git pull).
fc /b "backend\requirements.txt" "backend\.venv\requirements.instalado" >nul 2>&1
if errorlevel 1 (
  echo     Instalando os pacotes do Python [pode levar alguns minutos]...
  backend\.venv\Scripts\python.exe -m pip install --upgrade pip >nul
  backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt || goto erro_instalacao
  copy /y "backend\requirements.txt" "backend\.venv\requirements.instalado" >nul
)

echo [5/8] Front-end: pacotes do Node...
fc /b "frontend\package-lock.json" "frontend\node_modules\package-lock.instalado" >nul 2>&1
if errorlevel 1 (
  echo     Instalando os pacotes do Node [pode levar alguns minutos]...
  pushd frontend
  call npm install || (popd & goto erro_instalacao)
  popd
  copy /y "frontend\package-lock.json" "frontend\node_modules\package-lock.instalado" >nul
)

echo [6/8] Arquivos .env...
if not exist "frontend\.env" copy "frontend\.env.example" "frontend\.env" >nul
if exist "backend\.env" goto env_ok
copy "backend\.env.example" "backend\.env" >nul
rem Chave nova para cifrar as mensagens no banco. Como o banco desta
rem maquina comeca vazio, uma chave nova nao perde nada.
backend\.venv\Scripts\python.exe -c "import re,pathlib;from cryptography.fernet import Fernet;p=pathlib.Path('backend/.env');t=p.read_text('utf-8');p.write_text(re.sub(r'(?m)^DATA_ENCRYPTION_KEY=[ \t]*$','DATA_ENCRYPTION_KEY='+Fernet.generate_key().decode(),t),'utf-8')"
echo.
echo     Criei o backend\.env a partir do exemplo, com uma chave de
echo     criptografia nova. Faltam as chaves das integracoes. O mais facil
echo     e copiar o backend\.env do outro computador por cima deste.
echo     Se for preencher na mao, o minimo e:
echo       ANTHROPIC_API_KEY  - para a SelenIA responder
echo       GOOGLE_CLIENT_ID   - para o login no painel
echo       ALLOWED_EMAILS     - seu e-mail, senao ninguem entra
echo.
echo     Vou abrir o arquivo no Bloco de Notas. Salve, feche e volte aqui.
start "" /wait notepad "backend\.env"
:env_ok

echo [7/8] Encerrando servidores antigos nas portas 8000 e 5173...
rem O --reload do uvicorn as vezes deixa um processo antigo preso na
rem porta 8000, servindo codigo velho. Melhor comecar do zero.
for %%P in (8000 5173) do (
  for /f "tokens=5" %%I in ('netstat -ano ^| findstr /r /c:":%%P .*LISTENING"') do taskkill /PID %%I /T /F >nul 2>&1
)
rem Quando o processo principal do uvicorn ja morreu, o netstat ainda
rem mostra o PID dele, e o processo filho (o que atende de verdade)
rem continua preso na porta. Encerra os uvicorn antigos e depois os
rem filhos cujo processo pai nao existe mais.
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'uvicorn app.main' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match 'spawn_main\(parent_pid=(\d+)' -and -not (Get-Process -Id $Matches[1] -ErrorAction SilentlyContinue) } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1
taskkill /IM ngrok.exe /F >nul 2>&1

echo [8/8] Subindo API, painel e tunel...
echo     API    http://127.0.0.1:8000
rem O --reload observa so a pasta app\: o ChromaDB grava em chroma_data\
rem a cada inicio da API, e observando o backend inteiro isso reiniciava
rem a API sem parar (e a resposta do WhatsApp, que espera 6 s, nunca saia).
start "SelenIA - API" cmd /k "cd /d backend && .venv\Scripts\python.exe -m alembic upgrade head && .venv\Scripts\python.exe -m uvicorn app.main:app --reload --reload-dir app"
echo     Painel http://localhost:5173
start "SelenIA - Painel" cmd /k "cd /d frontend && npm run dev"

rem O endereco fixo vem do PUBLIC_WEBHOOK_HOST do backend\.env. Por ele
rem so passa o webhook; o resto da API continua so nesta maquina.
set "WEBHOOK_HOST="
for /f "usebackq tokens=1,* delims==" %%A in ("backend\.env") do if /i "%%A"=="PUBLIC_WEBHOOK_HOST" set "WEBHOOK_HOST=%%B"
where ngrok >nul 2>&1
if errorlevel 1 (
  echo     ngrok nao encontrado: o WhatsApp nao recebe mensagens nesta sessao.
) else if not defined WEBHOOK_HOST (
  echo     PUBLIC_WEBHOOK_HOST vazio no backend\.env: tunel nao iniciado.
) else (
  start "SelenIA - Tunel" cmd /k "ngrok http --domain=%WEBHOOK_HOST% 8000"
)

rem Espera a API responder (ate 60 s) antes de abrir o navegador.
set /a TENTATIVAS=0
:espera_api
ping -n 3 127.0.0.1 >nul
curl -s -o nul http://127.0.0.1:8000/health && goto api_ok
set /a TENTATIVAS+=1
if %TENTATIVAS% lss 30 goto espera_api
echo.
echo A API nao respondeu em 60 segundos. Veja o erro na janela "SelenIA - API".
pause
exit /b 1
:api_ok
rem ?sair encerra a sessao salva no navegador: o teste comeca pelo login.
start "" "http://localhost:5173/?sair"
echo.
echo Tudo no ar. Pode fechar esta janela.
timeout /t 5 >nul
exit /b 0

:acha_python
rem So precisa do Python do sistema para criar o venv na primeira vez.
set "PY="
py -3.12 --version >nul 2>&1 && set "PY=py -3.12"
if not defined PY (
  python --version 2>nul | findstr /b /c:"Python 3.12" >nul && set "PY=python"
)
if not defined PY (
  echo     Falta o Python 3.12: https://www.python.org/downloads/
  echo     Na instalacao, marque "Add python.exe to PATH".
  set "FALTA=1"
)
exit /b 0

:erro_instalacao
echo.
echo A instalacao falhou. Veja a mensagem acima.
pause
exit /b 1
