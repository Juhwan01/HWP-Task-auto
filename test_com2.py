"""Test COM with proper setup - try different ProgID."""
import pythoncom
import win32com.client
import sys
import os
import time

pythoncom.CoInitialize()

try:
    # Try different ProgIDs
    for progid in ['HWPFrame.HwpObject', 'Hwp.HwpObject']:
        print(f'Trying: {progid}', flush=True)
        try:
            hwp = win32com.client.Dispatch(progid)
            print(f'  Created OK', flush=True)

            # Set visible to false
            try:
                hwp.XHwpWindows.Item(0).Visible = False
                print(f'  Set invisible', flush=True)
            except Exception as e:
                print(f'  Visibility error: {e}', flush=True)

            # Register module for file path security
            try:
                hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
                print(f'  Module registered', flush=True)
            except Exception as e:
                print(f'  Module error (OK): {e}', flush=True)

            # Open file
            filepath = os.path.abspath('1.2024년 강선미 직업평가계획서.hwp')
            print(f'  Opening file...', flush=True)

            # Try Open with minimal params
            result = hwp.Open(filepath)
            print(f'  Open result: {result}', flush=True)

            # Get text
            hwp.InitScan()
            texts = []
            for _ in range(500):
                state, text = hwp.GetText()
                if state <= 1:
                    break
                if text.strip():
                    texts.append(text)
            hwp.ReleaseScan()

            print(f'  Got {len(texts)} text parts', flush=True)
            if texts:
                print(f'  Sample: {texts[0][:100]}', flush=True)

            hwp.Clear(1)
            hwp.Quit()
            print('SUCCESS!', flush=True)
            break

        except Exception as e:
            print(f'  Failed: {e}', flush=True)
            try:
                hwp.Quit()
            except:
                pass

except Exception as e:
    print(f'FATAL: {e}', flush=True)
finally:
    pythoncom.CoUninitialize()
