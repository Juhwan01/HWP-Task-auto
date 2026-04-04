"""Save HWP files as TXT using COM automation."""
import win32com.client
import os
import sys
import time

def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    txt_dir = os.path.join(base_dir, 'txt_output')
    os.makedirs(txt_dir, exist_ok=True)

    files = sorted([f for f in os.listdir(base_dir) if f.endswith('.hwp')])

    try:
        hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
        hwp.XHwpWindows.Item(0).Visible = False
    except Exception as e:
        print(f'Failed to create HWP COM object: {e}')
        sys.exit(1)

    try:
        hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
    except:
        pass

    for f in files:
        filepath = os.path.join(base_dir, f)
        txt_name = os.path.splitext(f)[0] + '.txt'
        txt_path = os.path.join(txt_dir, txt_name)

        print(f'Processing: {f}')
        try:
            hwp.Open(filepath, 'HWP', 'forceopen:true')
            # Save as text
            hwp.SaveAs(txt_path, 'TEXT')
            hwp.Clear(1)  # Close without save prompt
            print(f'  -> Saved: {txt_name}')
        except Exception as e:
            print(f'  ERROR: {e}')

    try:
        hwp.Quit()
    except:
        pass

    print('Done.')


if __name__ == '__main__':
    main()
