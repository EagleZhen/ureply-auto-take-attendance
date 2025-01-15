@REM if exist dist\*.exe del /s /q dist\*.exe
@REM rmdir /s /q build
@REM del /f /q *.spec

pyinstaller --onefile --hidden-import plyer.platforms.win.notification --icon=icon_sleep.ico "ureply auto take attendance.py"
pyinstaller --onefile --icon=icon_wake.ico "publish ureply answers.py"
pyinstaller --onefile --icon=icon_penguin.ico "initialize info.py"