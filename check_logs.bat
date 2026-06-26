@echo off
echo.
echo === mf_worker.log ===
type "%TEMP%\mf_worker.log" 2>nul || echo (not found)
echo.
echo === mf_worker_stderr.log ===
type "%TEMP%\mf_worker_stderr.log" 2>nul || echo (not found)
echo.
pause
