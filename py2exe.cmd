pyinstaller --onefile --hidden-import plyer.platforms.win.notification "ureply auto take attendance.py"
pyinstaller --onefile "publish ureply answers.py"
pyinstaller --onefile "initialize info.py"