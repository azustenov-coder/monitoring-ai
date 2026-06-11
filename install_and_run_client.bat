@echo off
title Monitoring AI - O'rnatish
color 0A

echo ============================================
echo   MONITORING AI - O'RNATISH
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python topilmadi!
    echo [!] https://python.org dan yuklab oling
    echo     O'rnatishda "Add Python to PATH" belgilang!
    pause
    exit /b 1
)
echo [+] Python topildi

echo [*] Kutubxonalar o'rnatilmoqda...
python -m pip install pillow opencv-python --quiet --upgrade
echo [+] Tayyor

echo [*] Dastur ishga tushirilmoqda (fon rejimi)...
start /B pythonw classroom_client.py

echo.
echo ============================================
echo  [+] Monitoring dasturi ishga tushdi!
echo  Admin ekran va kamerangizni ko'radi.
echo ============================================
timeout /t 4
