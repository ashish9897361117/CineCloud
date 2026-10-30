@echo off
title CineCloud Streaming Server
echo ========================================================
echo   CineCloud - Personal Movie Streaming Platform
echo ========================================================
echo   Web App & Admin Studio: http://localhost:8080
echo   Android TV 10-Foot UI:  http://localhost:8080/#tv
echo   Local Network (TV/Phone): http://192.168.29.2:8080
echo ========================================================
echo Starting CineCloud server...
python backend\server.py
pause
