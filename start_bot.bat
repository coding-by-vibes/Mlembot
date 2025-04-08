@echo off
echo ==============================
echo Mlembot Boot Sequence Initiated
echo ==============================

REM Create virtual environment if it doesn't exist
if not exist mlembot (
    echo [Step 1/4] Creating virtual environment...
    python -m venv mlembot
)

REM Activate the virtual environment
echo [Step 2/4] Activating virtual environment...
call mlembot\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

REM Install dependencies from requirements.txt
echo [Step 3/4] Installing dependencies...
pip install -r requirements.txt

REM Run the bot
echo [Step 4/4] Starting Discord Bot...
python -m bot.main

REM Deactivate when finished
call mlembot\Scripts\deactivate.bat
echo Bot has shut down.
pause
