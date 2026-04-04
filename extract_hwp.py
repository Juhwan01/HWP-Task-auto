"""Extract text from HWP files using olefile + zlib decompression."""
import olefile
import zlib
import struct
import os
import json
import sys


def extract_hwp_text(filepath):
    """Extract all text from an HWP file."""
    ole = olefile.OleFileIO(filepath)

    texts = []

    # Try PrvText first (preview text, may be truncated)
    if ole.exists('PrvText'):
        prvtext = ole.openstream('PrvText').read()
        texts.append(('PrvText', prvtext.decode('UTF-16-LE', errors='replace').strip('\x00')))

    # Try to get FileHeader to check compression
    compressed = False
    if ole.exists('FileHeader'):
        header = ole.openstream('FileHeader').read()
        if len(header) > 36:
            flags = struct.unpack_from('<I', header, 36)[0]
            compressed = bool(flags & 1)

    # Parse BodyText sections
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

        # Parse HWP record format to extract text
        section_text = parse_section_text(raw)
        if section_text:
            texts.append((f'Section{section_idx}', section_text))

        section_idx += 1

    ole.close()
    return texts


def parse_section_text(data):
    """Parse HWP body section binary data to extract text."""
    text_parts = []
    offset = 0

    while offset < len(data) - 4:
        try:
            # HWP record header: 4 bytes
            header = struct.unpack_from('<I', data, offset)[0]
            tag_id = header & 0x3FF
            level = (header >> 10) & 0x3FF
            size = (header >> 20) & 0xFFF

            if size == 0xFFF:
                if offset + 8 > len(data):
                    break
                size = struct.unpack_from('<I', data, offset + 4)[0]
                offset += 8
            else:
                offset += 4

            if offset + size > len(data):
                break

            record_data = data[offset:offset + size]

            # HWPTAG_PARA_TEXT = 66 (base 0x42)
            if tag_id == 66:
                text = extract_para_text(record_data)
                if text.strip():
                    text_parts.append(text)

            offset += size

        except (struct.error, IndexError):
            break

    return '\n'.join(text_parts)


def extract_para_text(data):
    """Extract text from HWPTAG_PARA_TEXT record."""
    chars = []
    i = 0

    while i < len(data) - 1:
        code = struct.unpack_from('<H', data, i)[0]

        if code == 0:
            break
        elif code < 32:
            # Control characters
            if code in (1, 2, 3, 11, 12, 14, 15, 16, 17, 18, 21, 22, 23):
                # Inline controls - skip 8 bytes total (including the 2-byte code)
                i += 16  # 8 chars = 16 bytes
                continue
            elif code == 10:  # Line break
                chars.append('\n')
            elif code == 13:  # Para break
                chars.append('\n')
            elif code == 9:  # Tab
                chars.append('\t')
            elif code == 4:  # Field start
                i += 16
                continue
            elif code == 24:  # Hyphen
                chars.append('-')
            elif code == 30:  # Non-breaking space
                chars.append(' ')
            elif code == 31:  # Fixed-width space
                chars.append(' ')
            else:
                i += 2
                continue
        else:
            chars.append(chr(code))

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
            texts = extract_hwp_text(filepath)
            # Combine all text sources
            all_text = ''
            for source, text in texts:
                all_text += f'\n--- {source} ---\n{text}\n'
            output[f] = all_text.strip()
            print(f'  OK: {len(all_text)} chars', file=sys.stderr)
        except Exception as e:
            output[f] = f'ERROR: {e}'
            print(f'  ERROR: {e}', file=sys.stderr)

    # Save as JSON
    output_path = os.path.join(base_dir, 'extracted_texts.json')
    with open(output_path, 'w', encoding='utf-8') as fp:
        json.dump(output, fp, ensure_ascii=False, indent=2)

    print(f'\nSaved to {output_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
