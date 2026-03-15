import traceback
try:
    from gui.app import StegoApp
    app = StegoApp()
    app.mainloop()
except Exception as e:
    traceback.print_exc()
    with open("crash_log.txt", "w") as f:
        traceback.print_exc(file=f)
