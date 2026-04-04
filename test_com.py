"""Quick COM test with proper initialization."""
import pythoncom
import win32com.client
import sys
import os

pythoncom.CoInitialize()

try:
    hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
    hwp.XHwpWindows.Item(0).Visible = False
    try:
        hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
    except:
        pass

    # Open a small file
    filepath = os.path.abspath('1.2024년 강선미 직업평가계획서.hwp')
    print(f'Opening: {filepath}', flush=True)

    result = hwp.Open(filepath, 'HWP', 'forceopen:true')
    print(f'Open result: {result}', flush=True)

    # Try to get text using SelectAll + GetSelectedText
    act = hwp.CreateAction('SelectAll')
    act.Execute()

    # Try GetText approach
    hwp.InitScan()
    texts = []
    count = 0
    while count < 1000:  # safety limit
        state, text = hwp.GetText()
        if state in (0, 1):
            break
        if text.strip():
            texts.append(text)
        count += 1
    hwp.ReleaseScan()

    full_text = '\n'.join(texts)
    print(f'Got {len(full_text)} chars, {len(texts)} parts', flush=True)
    print(full_text[:500], flush=True)

    hwp.Clear(1)
    hwp.Quit()
    print('SUCCESS', flush=True)

except Exception as e:
    print(f'ERROR: {e}', flush=True)
    import traceback
    traceback.print_exc()
finally:
    pythoncom.CoUninitialize()
