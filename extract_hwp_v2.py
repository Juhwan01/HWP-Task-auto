"""Extract text from HWP files - improved body text parsing."""
import olefile
import zlib
import struct
import os
import json
import sys


def extract_hwp_text(filepath):
    """Extract all text from an HWP file."""
    ole = olefile.OleFileIO(filepath)

    # List all streams for debugging
    streams = ole.listdir()

    # Check compression flag in FileHeader
    compressed = False
    if ole.exists('FileHeader'):
        header = ole.openstream('FileHeader').read()
        if len(header) > 36:
            flags = struct.unpack_from('<I', header, 36)[0]
            compressed = bool(flags & 1)

    # Get PrvText (preview - may be truncated but clean)
    prvtext = ''
    if ole.exists('PrvText'):
        raw = ole.openstream('PrvText').read()
        prvtext = raw.decode('UTF-16-LE', errors='replace').rstrip('\x00')

    # Parse BodyText sections for full text
    body_text = ''
    section_idx = 0
    while True:
        section_name = f'BodyText/Section{section_idx}'
        if not ole.exists(section_name):
            break

        raw = ole.openstream(section_name).read()

        if compressed:
            try:
                raw = zlib.decompress(raw, -15)
            except zlib.error:
                try:
                    raw = zlib.decompress(raw)
                except zlib.error:
                    section_idx += 1
                    continue

        section_text = parse_hwp5_body(raw)
        if section_text:
            body_text += section_text + '\n'

        section_idx += 1

    ole.close()

    # Use body_text if it has more content, otherwise fall back to PrvText
    if len(body_text.strip()) > len(prvtext.strip()):
        return body_text.strip()
    else:
        return prvtext.strip()


HWPTAG_BEGIN = 0x010  # 16
HWPTAG_PARA_HEADER = HWPTAG_BEGIN + 50  # 66
HWPTAG_PARA_TEXT = HWPTAG_BEGIN + 51    # 67


def parse_hwp5_body(data):
    """Parse HWP5 body section to extract paragraph text."""
    text_parts = []
    offset = 0

    while offset < len(data) - 4:
        try:
            header_val = struct.unpack_from('<I', data, offset)[0]
            tag_id = header_val & 0x3FF
            level = (header_val >> 10) & 0x3FF
            size = (header_val >> 20) & 0xFFF

            if size == 0xFFF:
                if offset + 8 > len(data):
                    break
                size = struct.unpack_from('<I', data, offset + 4)[0]
                offset += 8
            else:
                offset += 4

            if size < 0 or offset + size > len(data):
                break

            record_data = data[offset:offset + size]

            # HWPTAG_PARA_TEXT = 67
            if tag_id == 67:
                text = decode_para_text(record_data)
                if text.strip():
                    text_parts.append(text)

            offset += size

        except (struct.error, IndexError):
            break

    return '\n'.join(text_parts)


def decode_para_text(data):
    """Decode HWPTAG_PARA_TEXT record into text."""
    chars = []
    i = 0
    length = len(data)

    while i < length - 1:
        wch = struct.unpack_from('<H', data, i)[0]

        if wch == 0:
            # Null terminator
            break

        # Extended control characters (occupy 8 wchars = 16 bytes)
        if wch in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23):
            if wch == 10:  # Line break
                chars.append('\n')
                i += 2
            elif wch == 13:  # Paragraph end
                chars.append('\n')
                i += 2
            elif wch == 9:  # Tab
                chars.append('\t')
                i += 2
            elif wch == 24:
                chars.append('-')
                i += 2
            elif wch == 30 or wch == 31:
                chars.append(' ')
                i += 2
            elif wch in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
                # Inline/extended controls: skip 16 bytes total
                i += 16
            elif wch in (4, 5, 6, 7, 8, 19, 20):
                # Extended controls
                i += 16
            else:
                i += 2
        else:
            chars.append(chr(wch))
            i += 2

    return ''.join(chars)


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    files = sorted([f for f in os.listdir(base_dir) if f.endswith('.hwp')])

    output = {}

    for f in files:
        filepath = os.path.join(base_dir, f)
        print(f'Processing: {f}', file=sys.stderr)
        try:
            text = extract_hwp_text(filepath)
            output[f] = text
            print(f'  -> {len(text)} chars (source: {"body" if len(text) > 1000 else "prvtext"})', file=sys.stderr)
        except Exception as e:
            output[f] = f'ERROR: {e}'
            print(f'  ERROR: {e}', file=sys.stderr)

    output_path = os.path.join(base_dir, 'extracted_texts_v2.json')
    with open(output_path, 'w', encoding='utf-8') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)
    print(f'\nSaved to {output_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
