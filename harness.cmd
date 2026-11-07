@echo off
rem MAH launcher for Windows: double-click to open the menu, or pass a command:
rem   harness.cmd start C:\path\to\repo
setlocal
set "BASH="
for %%P in ("%ProgramFiles%\Git\bin\bash.exe" "%ProgramFiles(x86)%\Git\bin\bash.exe" "%LocalAppData%\Programs\Git\bin\bash.exe") do (
  if exist %%P if not defined BASH set "BASH=%%~P"
)
if not defined BASH for /f "delims=" %%B in ('where bash 2^>nul') do if not defined BASH set "BASH=%%B"
if not defined BASH (
  echo Git Bash not found. Install Git for Windows: https://git-scm.com/download/win
  pause
  exit /b 1
)
"%BASH%" "%~dp0harness.sh" %*
set "RC=%ERRORLEVEL%"
if "%~1"=="" pause
exit /b %RC%
