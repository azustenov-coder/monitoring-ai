@echo off
title Monitoring AI - To'xtatish va O'chirish
color 0C

echo ============================================
echo   MONITORING AI - CLIENTNI TO'XTATISH
echo ============================================
echo.

echo [*] Orqa fondagi jarayon to'xtatilmoqda...
taskkill /f /im pythonw.exe >nul 2>&1

echo [*] Avtomatik ishga tushish (Startup) ro'yxatidan o'chirilmoqda...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "MonitoringAIClient" /f >nul 2>&1

echo.
echo ============================================
echo  [+] Client to'liq to'xtatildi va o'chirildi!
echo ============================================
echo.
pause
