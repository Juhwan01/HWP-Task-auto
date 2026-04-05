"""현장평가지 HWP 텍스트 파서.

현장평가 HWP에서 추출한 텍스트를 파싱하여
영역별 항목, 점수, 수행율 등 구조화된 데이터를 반환한다.
"""
import re


# 영역 정의: (영역명, 섹션 시작 패턴, 섹션 종료 패턴)
SECTIONS = [
    ('작업규칙', r'1\.\s*작업규칙\s*영역', r'2\.\s*작업태도\s*영역'),
    ('작업태도', r'2\.\s*작업태도\s*영역', r'3\.\s*의사소통'),
    ('의사소통', r'3\.\s*의사소통', r'4\.\s*직무기술'),
    ('직무기술', r'4\.\s*직무기술', r'평\s*가\s*결\s*과'),
]

# 무시할 행 (헤더, 라벨 등)
SKIP_PATTERNS = [
    r'^항\s*목$', r'^직무수행\s*단계$', r'^[1-5]$',
    r'^작업규칙$', r'^작업태도$', r'^의사소통$', r'^대인관계$',
    r'^/\s*$', r'^/$',
    r'^총\s*점', r'^\d+점?\s*/\s*\d+점?$', r'^\d+\s*/\s*\d+점$',
    r'^책무$', r'^순번$', r'^작업명$', r'^과\s*제\s*항\s*목$',
    r'^세$', r'^탁$', r'^물$', r'^건$', r'^조$',
    r'^\d+$',
]

# 직무기술 작업명 (항목이 아닌 헤더)
TASK_HEADERS = [
    '아이로너로 건조하기', '건조기로 건조하기',
    '세탁기로 세탁하기', '포장하기', '다림질하기',
]


def parse_eval_text(raw_text):
    """현장평가 전체 텍스트를 파싱하여 구조화된 dict 반환.

    Returns:
        {
            'basic_info': { name, birth_date, eval_date, disability, case_manager, job },
            'sections': {
                '작업규칙': {
                    'items': [{'text': str, 'score': int}, ...],
                    'score': int,
                    'total': int,
                    'pct': float,
                },
                ...
            },
            'summary': {
                'total_score': int,
                'total_possible': int,
                'total_pct': float,
            },
            'opinion': str,
        }
    """
    lines = re.split(r'\r?\n', raw_text)
    lines = [l.strip() for l in lines]

    result = {
        'basic_info': _parse_basic_info(lines),
        'sections': {},
        'summary': {},
        'opinion': '',
    }

    for section_name, start_pat, end_pat in SECTIONS:
        section_text = _extract_section(raw_text, start_pat, end_pat)
        if section_text:
            result['sections'][section_name] = _parse_section(section_text, section_name)

    result['summary'] = _parse_summary(raw_text)
    result['opinion'] = _parse_opinion(raw_text)

    return result


def _parse_basic_info(lines):
    info = {}
    field_map = {
        '이름': 'name',
        '생년월일': 'birth_date',
        '평가일': 'eval_date',
        '장애명(등급)': 'disability',
        '사례관리자': 'case_manager',
        '담당직무': 'job',
    }
    for i, line in enumerate(lines):
        for label, key in field_map.items():
            if line == label and i + 1 < len(lines):
                val = lines[i + 1].replace('   ', ' ').strip()
                if val:
                    info[key] = val
    return info


def _extract_section(raw_text, start_pat, end_pat):
    match = re.search(start_pat, raw_text)
    if not match:
        return ''
    start = match.end()
    end_match = re.search(end_pat, raw_text[start:])
    if end_match:
        return raw_text[start:start + end_match.start()]
    return raw_text[start:]


def _is_skip_line(line):
    if not line:
        return True
    for pat in SKIP_PATTERNS:
        if re.match(pat, line):
            return True
    return False


def _is_item_text(line, section_name):
    if not line or len(line) < 5:
        return False
    if _is_skip_line(line):
        return False
    if line in TASK_HEADERS:
        return False
    if re.match(r'^0$', line):
        return False
    # 항목은 한글 문장 (마침표, 동사 어미 등으로 끝남)
    if re.search(r'[다된는음]\s*\.?\s*$', line) or re.search(r'있다$|한다$|않는다$|된다$|구한다$', line):
        return True
    # "수 있다" 패턴
    if re.search(r'수\s*있다$', line):
        return True
    # 괄호로 끝나는 항목: "사용한다.(존대하기 등)"
    if re.search(r'[다된는음]\s*\.\s*\([^)]+\)\s*$', line):
        return True
    return False


def _parse_section(section_text, section_name):
    lines = re.split(r'\r?\n', section_text)
    lines = [l.strip() for l in lines]

    items = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # 총점 라인 감지
        if re.match(r'^총\s*점', line):
            score_match = re.search(r'(\d+)\s*점?\s*/\s*(\d+)\s*점?', lines[i + 1] if i + 1 < len(lines) else '')
            if not score_match:
                score_match = re.search(r'(\d+)\s*점?\s*/\s*(\d+)\s*점?', line)
            if score_match:
                total_score = int(score_match.group(1))
                total_possible = int(score_match.group(2))
            break

        # 항목 텍스트 감지
        if _is_item_text(line, section_name):
            # 다음 줄들에서 "0" 위치 찾기 (점수)
            score = _find_score_after(lines, i + 1)
            if score > 0:
                items.append({'text': line, 'score': score})
            i += 1
            continue

        # 여러 줄로 이어지는 항목 (줄바꿈 포함)
        if line and not _is_skip_line(line) and line not in TASK_HEADERS and not re.match(r'^0$', line):
            # 다음 줄과 합쳐서 항목인지 확인
            if i + 1 < len(lines) and lines[i + 1] and not _is_skip_line(lines[i + 1]):
                combined = line + ' ' + lines[i + 1]
                if _is_item_text(combined, section_name):
                    score = _find_score_after(lines, i + 2)
                    if score > 0:
                        items.append({'text': combined, 'score': score})
                        i += 2
                        continue

        i += 1

    # 항목 점수 합산 (기본값)
    total_score_val = sum(it['score'] for it in items)
    total_possible_val = len(items) * 5

    # 텍스트에서 총점 직접 추출
    score_match = re.search(r'총\s*점\s*\r?\n?\s*(\d+)\s*점?\s*/\s*(\d+)\s*점?', section_text)
    if score_match:
        total_score_val = int(score_match.group(1))
        total_possible_val = int(score_match.group(2))

    pct = round(total_score_val / total_possible_val * 100, 1) if total_possible_val > 0 else 0

    return {
        'items': items,
        'score': total_score_val,
        'total': total_possible_val,
        'pct': pct,
    }


def _find_score_after(lines, start_idx):
    """lines[start_idx]부터 탐색하여 "0"의 위치(1~5)를 점수로 반환."""
    cells = []
    for j in range(start_idx, min(start_idx + 6, len(lines))):
        line = lines[j]
        # 다음 항목이나 총점에 도달하면 중단
        if _is_item_text(line, '') or re.match(r'^총\s*점', line):
            break
        if line == '0':
            cells.append('0')
        elif line == '' or _is_skip_line(line):
            cells.append('')
        else:
            break

    # "0"의 위치 = 점수 (1~5)
    if '0' in cells:
        return cells.index('0') + 1
    return 0


def _parse_summary(raw_text):
    """평가결과 요약표 파싱."""
    summary = {
        'total_score': 0,
        'total_possible': 0,
        'total_pct': 0.0,
    }

    # "전체 평균 수행율" 패턴: 94% (273점/290점)
    match = re.search(r'전체\s*평균\s*수행율\s*\r?\n?\s*(\d+)%\s*\((\d+)점\s*/\s*(\d+)점\)', raw_text)
    if match:
        summary['total_pct'] = float(match.group(1))
        summary['total_score'] = int(match.group(2))
        summary['total_possible'] = int(match.group(3))

    return summary


def _parse_opinion(raw_text):
    """종합소견 파싱."""
    match = re.search(r'종\s*합\s*소\s*견\s*\r?\n(.*)', raw_text, re.DOTALL)
    if match:
        text = match.group(1).strip()
        # 빈 줄만 있으면 빈 문자열
        if text.replace('\r', '').replace('\n', '').strip():
            return text.strip()
    return ''


def format_for_prompt(parsed):
    """파싱된 데이터를 AI 프롬프트에 삽입할 텍스트로 변환."""
    lines = []
    info = parsed['basic_info']
    lines.append(f"[대상자] {info.get('name', '')} / {info.get('disability', '')} / {info.get('job', '')}")
    lines.append(f"[평가일] {info.get('eval_date', '')}")
    lines.append('')

    for section_name, data in parsed['sections'].items():
        lines.append(f"## {section_name} ({data['score']}/{data['total']}, {data['pct']}%)")

        # 강점 (5점) / 보통 (4점) / 약점 (3점 이하) 분류
        strengths = [it for it in data['items'] if it['score'] == 5]
        moderate = [it for it in data['items'] if it['score'] == 4]
        weak = [it for it in data['items'] if it['score'] <= 3]

        if strengths:
            lines.append(f"  강점(5점, {len(strengths)}개): " + '; '.join(it['text'] for it in strengths))
        if moderate:
            lines.append(f"  보통(4점, {len(moderate)}개): " + '; '.join(it['text'] for it in moderate))
        if weak:
            for it in weak:
                lines.append(f"  약점({it['score']}점): {it['text']}")
        lines.append('')

    s = parsed['summary']
    lines.append(f"[전체] {s['total_score']}/{s['total_possible']} ({s['total_pct']}%)")

    if parsed['opinion']:
        lines.append(f"\n[종합소견] {parsed['opinion']}")

    return '\n'.join(lines)


def compare_years(prev_parsed, curr_parsed):
    """두 연도의 파싱 결과를 비교하여 변화 분석 텍스트 반환.

    Args:
        prev_parsed: 전년도 parse_eval_text() 결과
        curr_parsed: 금년도 parse_eval_text() 결과

    Returns:
        str: 프롬프트용 변화 분석 텍스트
    """
    lines = []
    prev_s = prev_parsed['summary']
    curr_s = curr_parsed['summary']

    total_diff = curr_s['total_score'] - prev_s['total_score']
    pct_diff = curr_s['total_pct'] - prev_s['total_pct']
    direction = '상승' if total_diff > 0 else ('하락' if total_diff < 0 else '동일')
    lines.append(f"[전체 변화] {prev_s['total_score']}점→{curr_s['total_score']}점 "
                 f"({prev_s['total_pct']}%→{curr_s['total_pct']}%, {direction})")
    lines.append('')

    section_map = {'작업규칙': '작업규칙', '작업태도': '작업태도',
                   '의사소통': '의사소통/대인관계', '직무기술': '직무기술'}

    improved = []
    declined = []
    maintained = []

    for section_name in ['작업규칙', '작업태도', '의사소통', '직무기술']:
        prev_sec = prev_parsed['sections'].get(section_name, {})
        curr_sec = curr_parsed['sections'].get(section_name, {})
        if not prev_sec or not curr_sec:
            continue

        p_score = prev_sec['score']
        c_score = curr_sec['score']
        p_pct = prev_sec['pct']
        c_pct = curr_sec['pct']
        diff = c_score - p_score
        label = section_map[section_name]

        if diff > 0:
            improved.append(f"{label}: {p_score}→{c_score}점 ({p_pct}%→{c_pct}%, +{diff}점)")
        elif diff < 0:
            declined.append(f"{label}: {p_score}→{c_score}점 ({p_pct}%→{c_pct}%, {diff}점)")
        else:
            maintained.append(f"{label}: {c_score}점 ({c_pct}%, 유지)")

    if improved:
        lines.append("[개선 영역] " + ' / '.join(improved))
    if declined:
        lines.append("[하락 영역] " + ' / '.join(declined))
    if maintained:
        lines.append("[유지 영역] " + ' / '.join(maintained))

    return '\n'.join(lines)


def load_eval_parsed(year, base_dir=None):
    """특정 연도의 현장평가 텍스트를 로드하고 파싱하여 반환.

    탐색 순서: {year}_eval_raw.txt → eval_raw_text.txt(연도 확인) → extracted_com.json fallback.
    """
    import os
    if base_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 파일 우선 시도
    candidates = [
        os.path.join(base_dir, f'{year}_eval_raw.txt'),
        os.path.join(base_dir, 'eval_raw_text.txt'),
    ]
    for path in candidates:
        if os.path.exists(path) and os.path.getsize(path) > 0:
            with open(path, 'r', encoding='utf-8') as f:
                text = f.read()
            if str(year) in text:
                return parse_eval_text(text)

    # fallback: extracted_com.json
    import json
    json_path = os.path.join(base_dir, 'extracted_com.json')
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, val in data.items():
            if str(year) in key and '현장' in key:
                return parse_eval_text(val)

    return None


if __name__ == '__main__':
    import json
    import sys
    sys.path.insert(0, '.')

    p2025 = load_eval_parsed(2025)
    p2024 = load_eval_parsed(2024)

    if p2025:
        print('=== 2025 프롬프트용 ===')
        print(format_for_prompt(p2025))

    if p2024 and p2025:
        print('\n=== 전년도 대비 변화 ===')
        print(compare_years(p2024, p2025))
