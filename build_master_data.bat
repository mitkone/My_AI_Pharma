@echo off
echo ========================================
echo СОЗДАВАНЕ НА MASTER DATA
echo ========================================
echo.
echo Този скрипт обработва всички Excel файлове
echo и създава master_data.csv като централна база данни.
echo.
pause

python create_master_data.py

echo.
echo ========================================
echo ГОТОВО!
echo ========================================
echo.
pause
