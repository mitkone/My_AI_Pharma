@echo off
echo Генериране на Parquet за бързо зареждане...
python build_parquet.py
if %errorlevel% equ 0 (
    echo.
    echo Готово! Добави pharma_data.parquet в Git и deploy.
    pause
) else (
    pause
)
