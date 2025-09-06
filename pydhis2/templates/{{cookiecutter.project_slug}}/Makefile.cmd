@echo off
REM {{ cookiecutter.project_name }} - Windows Batch Commands

if "%1"=="help" goto help
if "%1"=="setup" goto setup
if "%1"=="run-pipeline" goto run_pipeline
if "%1"=="dqr" goto dqr
if "%1"=="clean" goto clean
if "%1"=="" goto help

:help
echo.
echo {{ cookiecutter.project_name }} - Available Commands:
echo.
echo   make setup         - Install dependencies and set up the environment
echo   make run-pipeline  - Run the example data analysis pipeline
echo   make dqr           - Run data quality review
echo   make clean         - Clean up temporary files
echo   make help          - Display this help message
echo.
goto end

:setup
echo Setting up project environment...
if not exist venv (
    echo Creating virtual environment...
    py -m venv venv
)
echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat && pip install -r requirements.txt
echo Copying environment configuration file...
if not exist .env (
    copy env.example .env
    echo Please edit the .env file with your DHIS2 connection details
)
echo ✅ Environment setup complete!
goto end

:run_pipeline
echo Running data analysis pipeline...
if not exist venv (
    echo ❌ Please run 'make setup' first
    goto end
)
call venv\Scripts\activate.bat && py scripts/run_pipeline.py
goto end

:dqr
echo Running data quality review...
if not exist data\analytics_data.parquet (
    echo ❌ Data file not found. Please run 'make run-pipeline' first
    goto end
)
call venv\Scripts\activate.bat && pydhis2 dqr run --input data\analytics_data.parquet --html reports\dqr_report.html --json reports\dqr_summary.json
echo ✅ DQR report generated in the 'reports\' directory
goto end

:clean
echo Cleaning up temporary files...
if exist .pydhis2_cache rmdir /s /q .pydhis2_cache
if exist __pycache__ rmdir /s /q __pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache
echo ✅ Cleanup complete
goto end

:end
