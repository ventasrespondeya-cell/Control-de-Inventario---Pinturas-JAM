@echo off
echo ====================================================
echo SISTEMA PINTURAS JAM - SERVIDOR ACTIVO
echo ====================================================
echo IP de esta PC para conectar los telefonos:
ipconfig | findstr /i "IPv4"
echo ====================================================
echo Acceso en esta PC: http://localhost:5000
echo Acceso desde telefonos: Usa la IP mostrada arriba + :5000
echo ====================================================
start http://localhost:5000
python app.py
pause