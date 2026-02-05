import time
import win32api
import win32con

time.sleep(3)
win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
