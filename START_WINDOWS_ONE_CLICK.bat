@echo off
setlocal enabledelayedexpansion

cls
echo.
echo    SetupAgent AI - Windows One-Click Setup
echo    =========================================
echo.

REM Check Python
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo.
    echo Please install Python:
    echo 1. Visit https://python.org
    echo 2. Download Python 3.9 or higher
    echo 3. Install with "Add Python to PATH" checked
    echo.
    pause
    exit /b 1
)
echo OK - Python installed

REM Setup virtual environment
echo [2/5] Setting up virtual environment...
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat
echo OK - Virtual environment activated

REM Install dependencies
echo [3/5] Installing all required packages (this may take 2-3 minutes)...
echo.

python -m pip install --upgrade pip --quiet --no-warn-script-location

echo   Installing core packages...
pip install wheel setuptools --quiet --no-warn-script-location

echo   Installing CLI packages...
pip install click --quiet --no-warn-script-location
pip install pyyaml --quiet --no-warn-script-location
pip install python-dotenv --quiet --no-warn-script-location

echo   Installing async packages...
pip install aiofiles --quiet --no-warn-script-location

echo   Installing OpenAI package...
pip install openai --no-warn-script-location

echo   Installing Anthropic package...
pip install anthropic --no-warn-script-location

echo   Installing LangChain packages...
pip install langchain --quiet --no-warn-script-location
pip install langchain-core --quiet --no-warn-script-location
pip install langgraph --quiet --no-warn-script-location

echo   Installing utility packages...
pip install requests --quiet --no-warn-script-location
pip install gitpython --quiet --no-warn-script-location
pip install psutil --quiet --no-warn-script-location

echo.
echo OK - All dependencies installed

REM Configure API key
echo [4/5] Checking API key configuration...
if exist ".env" (
    echo OK - Found .env configuration file
    goto :run
)

if not "%OPENAI_API_KEY%"=="" (
    echo OK - Found API key in environment variable
    goto :run
)

echo.
echo =========================================
echo    API KEY CONFIGURATION
echo =========================================
echo.
echo Choose how to set up your API key:
echo.
echo   [1] Paste API key now
echo   [2] Create .env file manually
echo   [3] Skip for now
echo.
set /p setup="Enter your choice (1/2/3): "

if "%setup%"=="1" (
    echo.
    echo Choose your AI provider:
    echo   [1] OpenAI
    echo   [2] Anthropic
    echo.
    set /p provider="Select provider (1/2): "
    
    if "!provider!"=="1" (
        echo.
        echo -----------------------------------------
        echo PASTE INSTRUCTIONS:
        echo 1. Copy your OpenAI API key first
        echo 2. Right-click in this window to paste
        echo 3. Press Enter
        echo -----------------------------------------
        echo.
        set /p key="Paste API key here: "
        
        if "!key!"=="" (
            echo ERROR: No key entered
            pause
            exit /b 1
        )
        
        echo OPENAI_API_KEY=!key!> .env
        echo.
        echo OK - OpenAI API key saved
        
    ) else if "!provider!"=="2" (
        echo.
        echo -----------------------------------------
        echo PASTE INSTRUCTIONS:
        echo 1. Copy your Anthropic API key first
        echo 2. Right-click in this window to paste
        echo 3. Press Enter
        echo -----------------------------------------
        echo.
        set /p key="Paste API key here: "
        
        if "!key!"=="" (
            echo ERROR: No key entered
            pause
            exit /b 1
        )
        
        echo ANTHROPIC_API_KEY=!key!> .env
        echo PROVIDER=anthropic>> .env
        echo.
        echo OK - Anthropic API key saved
    )
    
) else if "%setup%"=="2" (
    echo.
    echo -----------------------------------------
    echo CREATE .env FILE MANUALLY:
    echo.
    echo 1. Create a new text file in this folder
    echo 2. Add this line:
    echo    OPENAI_API_KEY=your-api-key-here
    echo 3. Save as .env (not .env.txt)
    echo 4. Run this script again
    echo -----------------------------------------
    echo.
    pause
    exit /b 0
    
) else (
    echo.
    echo Skipping API key setup
    echo.
    pause
    exit /b 0
)

:run
echo [5/5] Starting SetupAgent AI...
echo.

REM Make sure we're in the right directory
cd /d "%~dp0"

REM Display current configuration
echo Current configuration:
if exist ".env" (
    echo - Using .env file for API key
) else if not "%OPENAI_API_KEY%"=="" (
    echo - Using environment variable for API key
) else if not "%ANTHROPIC_API_KEY%"=="" (
    echo - Using environment variable for API key
) else (
    echo - No API key configuration found
)

echo.
echo =========================================
echo    PROJECT SELECTION
echo =========================================
echo.

if "%1"=="" (
    echo Choose what to analyze:
    echo.
    echo   [1] Enter a GitHub repository URL
    echo   [2] Enter a local project path
    echo   [3] Analyze a test project (demo)
    echo   [4] Exit
    echo.
    set /p choice="Enter your choice (1/2/3/4): "
    
    if "!choice!"=="1" (
        echo.
        echo Enter GitHub repository URL:
        echo Example: https://github.com/username/project
        echo.
        set /p repo="GitHub URL: "
        
        if "!repo!"=="" (
            echo ERROR: No URL entered
            pause
            exit /b 1
        )
        
        echo.
        echo Analyzing repository: !repo!
        echo.
        python -m src.cli "!repo!"
        
    ) else if "!choice!"=="2" (
        echo.
        echo Enter the full path to your project:
        echo Example: C:\Users\YourName\Projects\MyProject
        echo.
        set /p projectpath="Project path: "
        
        if "!projectpath!"=="" (
            echo ERROR: No path entered
            pause
            exit /b 1
        )
        
        if not exist "!projectpath!" (
            echo ERROR: Path does not exist: !projectpath!
            pause
            exit /b 1
        )
        
        echo.
        echo Analyzing project: !projectpath!
        echo.
        python -m src.cli "!projectpath!"
        
    ) else if "!choice!"=="3" (
        echo.
        echo Creating test project for demonstration...
        
        REM Create a simple test project
        if not exist "test_project" mkdir test_project
        echo {"name": "test-app", "dependencies": {"express": "^4.18.0"}} > test_project\package.json
        echo print("Hello World") > test_project\app.py
        
        echo.
        echo Analyzing test project...
        echo.
        python -m src.cli test_project
        
    ) else (
        echo.
        echo Exiting...
        exit /b 0
    )
) else (
    echo Analyzing: %1
    echo.
    python -m src.cli %1
)

echo.
echo =========================================
echo Application finished
echo.
echo Press any key to exit...
pause >nul