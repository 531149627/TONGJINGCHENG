@echo off
title 桌面宠物启动中
cd /d "%~dp0"

set "UV_PATH=%USERPROFILE%\.local\bin\uv.exe"

if not exist "%UV_PATH%" (
    echo 找不到 uv 工具，请确认安装路径。
    pause
    exit /b
)

"%UV_PATH%" run --with pyqt6 python main.py

if %errorlevel% neq 0 (
    echo.
    echo 运行异常，错误码: %errorlevel%
    pause
)
