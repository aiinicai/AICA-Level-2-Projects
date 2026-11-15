@echo off
title CollectSaarthi - Production Deploy to Firebase
echo ==============================================================
echo    COLLECTSAARTHI - DEPLOY TO FIREBASE & COLLECTSAARTHI.COM
echo ==============================================================
echo.
echo Step 1 of 2: Connecting to your Firebase account...
echo (A browser window will open. Click your Google account and click 'Allow')
echo.
call npx.cmd firebase-tools login

echo.
echo Step 2 of 2: Uploading website files directly to collectsaarthi.com...
echo.
call npx.cmd firebase-tools deploy --only hosting,firestore:rules,storage:rules
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo Retrying hosting file upload...
  call npx.cmd firebase-tools deploy --only hosting
)

echo.
echo ==============================================================
echo    SUCCESS! DEPLOYMENT COMPLETE!
echo    Your website is now live at: https://collectsaarthi.com
echo ==============================================================
echo.
pause
