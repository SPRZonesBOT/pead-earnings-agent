@echo off
cd /d "G:\SPRZones\GitHub\pead-earnings-agent"

:: Python ka exact path do (agar environment variable set nahi hai toh)
:: Example: C:\Python311\python.exe
:: Agar "python" command chal raha hai toh woh use karo
python scheduler.py >> logs.txt 2>&1
