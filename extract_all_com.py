"""Extract full text from all HWP files using COM (HAction method)."""
import win32com.client
import os
import json
import sys

def extract_text(hwp, filepath):
    """Open a file and extract all text."""
    pset = hwp.HParameterSet.HFileOpenSave
    hwp.HAction.GetDefault('FileOpen', pset.HSet)
    pset.filename = filepath
    pset.Format = 'HWP'
    hwp.HAction.Execute('FileOpen', pset.HSet)

    hwp.InitScan()
    texts = []
    for _ in range(5000):
        state, text = hwp.GetText()
        if state <= 1:
            break
        texts.append(text)
    hwp.ReleaseScan()

    hwp.Clear(1)
    return '\n'.join(texts)


def main():
    base_dir = os.path.abspath(os.path.dirname(__file__))

    hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
    hwp.XHwpWindows.Item(0).Visible = False
    try:
        hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
    except:
        pass

    files = sorted([f for f in os.listdir(base_dir) if f.endswith('.hwp')])
    output = {}

    for f in files:
        filepath = os.path.join(base_dir, f)
        print(f'Processing: {f}', file=sys.stderr, flush=True)
        try:
            text = extract_text(hwp, filepath)
            output[f] = text
            print(f'  -> {len(text)} chars', file=sys.stderr, flush=True)
        except Exception as e:
            output[f] = f'ERROR: {e}'
            print(f'  ERROR: {e}', file=sys.stderr, flush=True)

    hwp.Quit()

    output_path = os.path.join(base_dir, 'extracted_com.json')
    with open(output_path, 'w', encoding='utf-8') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)
    print(f'Saved to {output_path}', file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
