@echo off

:: Check internet connection
ping -n 1 google.com >nul 2>nul
if errorlevel 1 (
    echo No internet connection. Skipping pip install.
) else (
    :: Create virtual environment if not exists
    if not exist venv (
        python -m venv venv
    )

    :: Activate virtual environment
    call venv\Scripts\activate

    :: Install required packages
    pip install --upgrade pip
    pip install tk tkinterdnd2
    pip install python-vlc
    pip install customtkinter
)

:: Activate virtual environment (if not already active)
if not defined VIRTUAL_ENV (
    call venv\Scripts\activate
)

:: Run the script
python compare_vid.py
pause

:: Deactivate virtual environment
deactivate
