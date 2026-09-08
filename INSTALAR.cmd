@echo off
setlocal EnableExtensions
title Instalador - Conversor DANFE
cd /d "%~dp0"

echo.
echo ============================================================
echo       INSTALADOR - CONVERSOR DANFE
echo ============================================================
echo.
echo Este processo cria o aplicativo e um atalho na Area de Trabalho.
echo A internet e necessaria apenas nesta primeira instalacao.
echo.

set "PYTHON_EXE="
for /f "delims=" %%P in ('py -3.12 -c "import sys, tkinter; tkinter.Tcl(); print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"

if not defined PYTHON_EXE (
    where winget >nul 2>&1
    if errorlevel 1 goto :no_python
    echo Python 3.12 completo nao encontrado. Instalando...
    winget install --id Python.Python.3.12 -e --scope user --force --accept-package-agreements --accept-source-agreements
    if errorlevel 1 goto :install_error
    for /f "delims=" %%P in ('py -3.12 -c "import sys, tkinter; tkinter.Tcl(); print(sys.executable)" 2^>nul') do set "PYTHON_EXE=%%P"
    if not defined PYTHON_EXE if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
)

if not defined PYTHON_EXE goto :python_incomplete
"%PYTHON_EXE%" -c "import tkinter; tkinter.Tcl()" >nul 2>&1
if errorlevel 1 goto :python_incomplete

echo Criando ambiente de compilacao...
if exist ".buildenv" rmdir /s /q ".buildenv"
"%PYTHON_EXE%" -m venv ".buildenv"
if errorlevel 1 goto :install_error

echo Instalando os componentes necessarios...
".buildenv\Scripts\python.exe" -m pip install --disable-pip-version-check --upgrade pip
if errorlevel 1 goto :install_error
".buildenv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto :install_error

echo Criando o aplicativo Windows...
".buildenv\Scripts\pyinstaller.exe" --noconfirm --clean --onefile --windowed ^
  --name "Conversor DANFE" ^
  conversor_danfe.py
if errorlevel 1 goto :install_error

copy /y "dist\Conversor DANFE.exe" "Conversor DANFE.exe" >nul
if errorlevel 1 goto :install_error

echo Criando atalho na Area de Trabalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Conversor DANFE.lnk');$s.TargetPath='%CD%\Conversor DANFE.exe';$s.WorkingDirectory='%CD%';$s.Description='Conversor local de XML NF-e para DANFE PDF';$s.Save()"

echo Limpando arquivos temporarios da instalacao...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist ".buildenv" rmdir /s /q ".buildenv"
if exist "Conversor DANFE.spec" del /q "Conversor DANFE.spec"

echo.
echo ============================================================
echo Instalacao concluida.
echo Use o atalho "Conversor DANFE" na Area de Trabalho.
echo ============================================================
echo.
start "" "Conversor DANFE.exe"
pause
exit /b 0

:no_python
echo.
echo Nao foi possivel localizar o Python nem o Winget.
echo Instale o Python 3.12 em https://www.python.org/downloads/windows/
echo Marque a opcao "Add Python to PATH" e execute este instalador novamente.
pause
exit /b 1

:python_incomplete
echo.
echo O Python foi localizado, mas o componente grafico Tcl/Tk nao esta completo.
echo Repare ou reinstale o Python 3.12 pelo site abaixo e marque "tcl/tk and IDLE":
echo https://www.python.org/downloads/windows/
pause
exit /b 1

:install_error
echo.
echo A instalacao nao foi concluida. Verifique sua conexao e tente novamente.
pause
exit /b 1
