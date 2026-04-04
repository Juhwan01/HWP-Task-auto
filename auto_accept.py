"""Open HWP file with auto-accept security dialog."""
import win32com.client
import win32gui
import win32con
import threading
import time
import os
import sys

def find_and_click_dialog():
    """Find HWP security dialog and click OK/허용."""
    for attempt in range(30):  # Try for 15 seconds
        time.sleep(0.5)
        
        def enum_callback(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                cls = win32gui.GetClassName(hwnd)
                if title and ('보안' in title or '경고' in title or '확인' in title 
                             or 'Security' in title or 'Warning' in title
                             or '한/글' in title or 'Hwp' in title):
                    results.append((hwnd, title, cls))
            return True
        
        results = []
        win32gui.EnumWindows(enum_callback, results)
        
        for hwnd, title, cls in results:
            print(f'  Dialog found: [{title}] ({cls})', flush=True)
            # Find and click buttons
            def find_button(child_hwnd, buttons):
                cls = win32gui.GetClassName(child_hwnd)
                text = win32gui.GetWindowText(child_hwnd)
                if cls == 'Button' and text:
                    buttons.append((child_hwnd, text))
                return True
            
            buttons = []
            win32gui.EnumChildWindows(hwnd, find_button, buttons)
            
            for btn_hwnd, btn_text in buttons:
                print(f'    Button: [{btn_text}]', flush=True)
                if any(k in btn_text for k in ['확인', '허용', '예', 'OK', 'Yes', 'Allow']):
                    print(f'    -> Clicking [{btn_text}]!', flush=True)
                    win32gui.PostMessage(btn_hwnd, win32con.BM_CLICK, 0, 0)
                    return True
    
    print('  No dialog found after 15 seconds', flush=True)
    return False

# Start dialog finder in background
t = threading.Thread(target=find_and_click_dialog, daemon=True)
t.start()

# COM
hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
hwp.XHwpWindows.Item(0).Visible = True  # Must be visible for dialogs
try:
    hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
except: pass

filepath = os.path.abspath('1.2024년 강선미 직업평가계획서.hwp')
print(f'Opening: {filepath}', flush=True)
hwp.Open(filepath, 'HWP', 'forceopen:true')
print('File opened!', flush=True)

hwp.InitScan()
texts = []
for _ in range(500):
    state, text = hwp.GetText()
    if state <= 1: break
    if text.strip(): texts.append(text)
hwp.ReleaseScan()
print(f'Extracted {len(texts)} text parts', flush=True)

hwp.Clear(1)
hwp.Quit()
print('SUCCESS', flush=True)
