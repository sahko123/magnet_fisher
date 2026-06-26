@echo off
setlocal

echo.
echo  ==========================================
echo   Magnet Fisher - Build
echo  ==========================================
echo.

:: Stop any running instance so files aren't locked
taskkill /F /IM MagnetFisher.exe >nul 2>&1
taskkill /F /IM torrent_worker.exe >nul 2>&1
timeout /t 1 /nobreak >nul

:: Check Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo  ERROR: python not found on PATH.
    pause & exit /b 1
)

:: Run PyInstaller  (use full path in case it's a user install)
set PYI=%APPDATA%\Python\Python313\Scripts\pyinstaller.exe
where pyinstaller >nul 2>&1 && set PYI=pyinstaller

echo  [1/2] Building with PyInstaller...
echo.
"%PYI%" magnet_fisher.spec -y
if errorlevel 1 (
    echo.
    echo  ERROR: PyInstaller failed. See output above.
    pause & exit /b 1
)

:: ────────────────────────────────────────────────────────────────────────────
:: PyInstaller 6.x puts files in _internal\.  Copy the Python + VC runtime
:: DLLs to the root so the Windows bootloader can always find them.
:: ────────────────────────────────────────────────────────────────────────────
echo  [2/2] Fixing DLL paths...
set OUT=dist\MagnetFisher
for %%F in (python3.dll python313.dll vcruntime140.dll vcruntime140_1.dll) do (
    if exist "%OUT%\_internal\%%F" (
        copy /Y "%OUT%\_internal\%%F" "%OUT%\" >nul
        echo         copied %%F
    )
)

echo.
echo  Done!  Output: %OUT%\MagnetFisher.exe
echo          Worker: %OUT%\torrent_worker.exe
echo.
echo  First run registers the magnet: handler automatically.
echo.

start "" "%OUT%"
pause
endlocal
