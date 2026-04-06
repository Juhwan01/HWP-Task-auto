"""에이전트 공통 베이스 모듈.

주요 함수:
- load_config, template_path, output_path: 설정/경로 유틸
- parse_ai_blocks, replace_blocks: AI 블록 파싱 및 HWP 교체
- load_eval_facts: 현장평가 팩트 로드 (mode='both'|'prev_only')
- enrich_cfg_from_eval: eval_parser 결과로 cfg scores 자동 동기화
- build_narrative_replacements: 서술문 점수/날짜 교체 쌍 생성
"""
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


def load_config(config_path=None):
    path = config_path or os.path.join(BASE_DIR, 'config.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def resolve_path(template_str, cfg):
    return template_str.format(
        base_year=cfg['base_year'],
        target_year=cfg['target_year'],
        name=cfg['name'],
    )


def template_path(cfg, key):
    filename = resolve_path(cfg['templates'][key], cfg)
    return os.path.join(BASE_DIR, 'templates', filename)


def output_path(cfg, key):
    filename = resolve_path(cfg['outputs'][key], cfg)
    return os.path.join(BASE_DIR, 'output', filename)


def txt_output_path(cfg, key, label):
    return os.path.join(BASE_DIR, 'output', f'_{key}_{label}.txt')


def save_txt(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def load_old_blocks(agent_name):
    """old_blocks/{agent_name}.json에서 OLD_BLOCKS를 로드."""
    path = os.path.join(BASE_DIR, 'old_blocks', f'{agent_name}.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _strip_markdown(text):
    """AI 응답에서 마크다운 문법을 제거하여 HWP용 순수 텍스트로 변환."""
    import re
    # **굵게** / __굵게__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # *기울임* / _기울임_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'\1', text)
    # ### 헤딩
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # --- 수평선
    text = re.sub(r'^-{3,}$', '', text, flags=re.MULTILINE)
    # 번호 목록 "1. " → "1. " 유지 (HWP에서도 자연스러움)
    # 불릿 "- " → 제거
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)
    return text


def parse_ai_blocks(text, expected_keys=None):
    """AI 응답에서 [블록:key] 형식 블록을 파싱.

    Args:
        text: AI 생성 텍스트
        expected_keys: 기대하는 키 목록 (검증용)

    Returns:
        dict: {key: content} 매핑
    """
    import re
    generated = {}
    cur_key = None
    cur_lines = []

    for line in text.split('\n'):
        # [블록:key] 또는 **[블록:key]** 등 다양한 형식 지원
        match = re.match(r'\[블록[:\s]*([^\]]+)\]', line.strip().strip('*'))
        if match:
            if cur_key:
                generated[cur_key] = _strip_markdown('\n'.join(cur_lines).strip())
            cur_key = match.group(1).strip()
            # 같은 줄에 내용이 이어질 수 있음
            rest = re.sub(r'\[블록[:\s]*[^\]]+\]\s*', '', line).strip()
            cur_lines = [rest] if rest else []
        else:
            cur_lines.append(line)

    if cur_key:
        generated[cur_key] = _strip_markdown('\n'.join(cur_lines).strip())

    if expected_keys:
        missing = [k for k in expected_keys if k not in generated or not generated[k]]
        if missing:
            print(f'  [경고] AI 블록 파싱 누락: {missing}', flush=True)

    return generated


def replace_blocks(hwp, old_blocks, generated, label='', ai=None, prompt=''):
    """OLD_BLOCKS를 AI 생성 텍스트로 교체. 실패 블록 목록 반환.

    블록 파싱이 전부 실패하면 ai를 사용해 재시도한다.
    """
    # 모든 블록이 비었으면 AI 재시도
    if ai and prompt and all(not generated.get(k, '') for k in old_blocks):
        print(f'  [재시도] {label}: 블록 파싱 전부 실패, AI 재호출', flush=True)
        retry_prompt = prompt + """

중요: 반드시 아래 형식으로 출력하세요. [블록:키이름] 줄을 먼저 쓰고 그 아래에 내용을 쓰세요.
형식을 정확히 지켜야 합니다. 예시:
[블록:example_key]
여기에 내용을 씁니다..."""
        retry_result = ai.generate(retry_prompt)
        generated = parse_ai_blocks(retry_result, expected_keys=list(old_blocks.keys()))

    failed = []
    for key, old_text in old_blocks.items():
        new_text = generated.get(key, '')
        if not new_text:
            print(f'  [스킵] {label} {key}: AI 생성 텍스트 없음', flush=True)
            failed.append(key)
            continue
        ok = hwp.find_replace_verified(old_text, new_text, label=f'{label} {key}')
        if not ok:
            failed.append(key)
    return failed


def validate_ai_output(text, cfg, year_key='curr_year'):
    """AI 생성 텍스트 내 점수가 cfg scores와 일치하는지 검증.

    "N점중 M점" 또는 "M/N" 패턴을 찾아 실제 점수와 대조한다.
    불일치 항목을 경고 출력하고 불일치 목록을 반환.
    """
    import re

    scores = cfg['scores'][year_key]
    # 영역별 (득점, 만점) 쌍
    expected = {
        '작업규칙': scores['rules'],
        '작업태도': scores['attitude'],
        '의사소통': scores['communication'],
        '직무기술': scores['skills'],
    }

    # 전체 합산
    total_score = sum(v[0] for v in expected.values())
    total_max = sum(v[1] for v in expected.values())
    total_pct = round(total_score / total_max * 100)

    mismatches = []

    # 패턴1: "N점중 M점" (만점중 득점)
    for m in re.finditer(r'(\d+)점중\s*(\d+)점', text):
        max_val, score_val = int(m.group(1)), int(m.group(2))
        # 100점중 XX점 = 전체 환산
        if max_val == 100:
            if score_val != total_pct:
                mismatches.append(f'전체 환산: 텍스트 {score_val}점 != 기대 {total_pct}점')
            continue
        # 영역별 매칭
        matched = False
        for name, (exp_sc, exp_tot) in expected.items():
            if max_val == exp_tot:
                if score_val != exp_sc:
                    mismatches.append(f'{name}: 텍스트 {score_val}/{max_val} != 기대 {exp_sc}/{exp_tot}')
                matched = True
                break
        if not matched and max_val not in [100]:
            mismatches.append(f'미식별 점수: {score_val}/{max_val}')

    # 패턴2: "XX%의 수행율" 또는 "XX%수행율"
    for m in re.finditer(r'(\d+)%\s*(?:의\s*)?수행율', text):
        pct_val = int(m.group(1))
        valid_pcts = {round(v[0] / v[1] * 100) for v in expected.values()}
        valid_pcts.add(total_pct)
        if pct_val not in valid_pcts:
            mismatches.append(f'수행율 {pct_val}%가 어떤 영역과도 불일치')

    if mismatches:
        for msg in mismatches:
            print(f'  [수치검증] {msg}', flush=True)

    return mismatches


def load_eval_facts(cfg, mode='both'):
    """현장평가 팩트를 로드하여 프롬프트용 데이터를 반환.

    Args:
        cfg: config dict
        mode: 'both' (curr+prev, agent_03~05) 또는 'prev_only' (agent_02)

    Returns:
        dict with keys:
            parsed_curr, parsed_prev, facts, changes,
            weak_items, moderate_items, weak_detail, moderate_detail
    """
    from core.eval_parser import load_eval_parsed, format_for_prompt, compare_years

    ty = cfg['target_year']
    by = cfg['base_year']

    parsed_prev = load_eval_parsed(by)
    parsed_curr = None
    facts = ''
    changes = ''

    if mode == 'prev_only':
        facts = format_for_prompt(parsed_prev) if parsed_prev else ''
        comm_source = parsed_prev
    else:
        parsed_curr = load_eval_parsed(ty)
        facts = format_for_prompt(parsed_curr) if parsed_curr else ''
        changes = compare_years(parsed_prev, parsed_curr) if (parsed_prev and parsed_curr) else ''
        comm_source = parsed_curr

    # 의사소통 약점/보통 항목 추출
    comm_section = comm_source['sections'].get('의사소통', {}) if comm_source else {}
    weak_items = [it for it in comm_section.get('items', []) if it['score'] <= 3]
    moderate_items = [it for it in comm_section.get('items', []) if it['score'] == 4]
    weak_detail = '\n'.join(f"  - {it['text']} ({it['score']}점)" for it in weak_items)
    moderate_detail = '\n'.join(f"  - {it['text']} (4점)" for it in moderate_items)

    prev_total_pct = parsed_prev['summary']['total_pct'] if parsed_prev else 'N/A'
    curr_total_pct = parsed_curr['summary']['total_pct'] if parsed_curr else 'N/A'

    return {
        'parsed_curr': parsed_curr,
        'parsed_prev': parsed_prev,
        'prev_total_pct': prev_total_pct,
        'curr_total_pct': curr_total_pct,
        'facts': facts,
        'changes': changes,
        'weak_items': weak_items,
        'moderate_items': moderate_items,
        'weak_detail': weak_detail,
        'moderate_detail': moderate_detail,
    }


def enrich_cfg_from_eval(cfg):
    """eval_parser 결과로 cfg['scores']를 자동 갱신. 불일치 시 경고 출력.

    config.json의 수동 입력 점수와 현장평가 파서 결과를 동기화한다.
    파서 결과가 없으면 기존 cfg를 그대로 반환.
    """
    from core.eval_parser import load_eval_parsed

    section_key_map = {
        '작업규칙': 'rules',
        '작업태도': 'attitude',
        '의사소통': 'communication',
        '직무기술': 'skills',
    }

    year_map = {
        'curr_year': cfg['target_year'],
        'prev_year': cfg['base_year'],
    }

    for cfg_key, year in year_map.items():
        parsed = load_eval_parsed(year)
        if not parsed:
            continue

        for section_name, score_key in section_key_map.items():
            section = parsed['sections'].get(section_name)
            if not section:
                continue

            old = cfg['scores'][cfg_key].get(score_key, [0, 0])
            new = [section['score'], section['total']]

            if old != new:
                print(f'  [동기화] {year}년 {section_name}: config {old} → eval_parser {new}', flush=True)
                cfg['scores'][cfg_key][score_key] = new

    return cfg


def calc_pct(score, total):
    return round(score / total * 100)


def pct_str(score, total):
    return f'{calc_pct(score, total)}%'


def score_summary(cfg, year_key='curr_year'):
    s = cfg['scores'][year_key]
    lines = []
    for label, key in [('작업규칙', 'rules'), ('작업태도', 'attitude'),
                        ('의사소통/대인관계', 'communication'), ('직무기술', 'skills')]:
        sc, tot = s[key]
        lines.append(f'  * {label}: {sc}/{tot} ({pct_str(sc, tot)})')
    total_sc = sum(s[k][0] for k in ['rules', 'attitude', 'communication', 'skills'])
    total_tot = sum(s[k][1] for k in ['rules', 'attitude', 'communication', 'skills'])
    lines.append(f'  * 전체: {total_sc}/{total_tot} ({pct_str(total_sc, total_tot)})')
    return '\n'.join(lines)


def run_standalone(run_fn, needs_ai=False):
    """에이전트 단독 실행용 헬퍼. __main__ 블록 중복을 제거한다.

    Args:
        run_fn: 에이전트의 run(cfg, hwp[, ai]) 함수
        needs_ai: True이면 AiEngine도 생성하여 전달
    """
    from core.hwp_engine import HwpEngine

    cfg = load_config()
    hwp = HwpEngine()
    try:
        if needs_ai:
            from core.ai_engine import AiEngine
            ai = AiEngine()
            print(run_fn(cfg, hwp, ai))
        else:
            print(run_fn(cfg, hwp))
    finally:
        hwp.quit()


def build_narrative_replacements(cfg):
    """서술문 안의 모든 점수/팩트 참조를 교체하는 replacement 쌍 목록 생성.

    모든 에이전트가 공통으로 사용. 표 셀 뿐 아니라 서술문 안의
    '100점중 93점', '110점중 100점을 얻어 91%' 등을 전부 교체한다.
    """
    by = cfg['base_year']
    ty = cfg['target_year']
    prev = cfg['scores']['prev_year']
    curr = cfg['scores']['curr_year']

    p_att_sc, p_att_tot = prev['attitude']
    c_att_sc, c_att_tot = curr['attitude']
    p_comm_sc, p_comm_tot = prev['communication']
    c_comm_sc, c_comm_tot = curr['communication']

    p_total = sum(prev[k][0] for k in ['rules', 'attitude', 'communication', 'skills'])
    c_total = sum(curr[k][0] for k in ['rules', 'attitude', 'communication', 'skills'])
    p_all = sum(prev[k][1] for k in ['rules', 'attitude', 'communication', 'skills'])
    p_overall_pct = calc_pct(p_total, p_all)
    c_overall_pct = calc_pct(c_total, p_all)

    # 전전년도 (진전도 비교용)
    pp_overall_pct = p_overall_pct - 1  # 근사값 (92%→93%→94%)

    # 교체 순서 중요: 긴 문자열(구체적)부터, 짧은 문자열(일반적)은 나중에
    replacements = [
        # === 1. 가장 구체적인 서술문 패턴부터 (충돌 방지) ===

        # "110점중 100점을 얻어 91%" → "110점중 101점을 얻어 92%" (작업태도)
        (f'{p_att_tot}점중 {p_att_sc}점을 얻어 {calc_pct(p_att_sc, p_att_tot)}%',
         f'{c_att_tot}점중 {c_att_sc}점을 얻어 {calc_pct(c_att_sc, c_att_tot)}%'),

        # "90점중 80점을 얻어 89%" → "90점중 82점을 얻어 91%" (의사소통)
        (f'{p_comm_tot}점중 {p_comm_sc}점을 얻어 {calc_pct(p_comm_sc, p_comm_tot)}%',
         f'{c_comm_tot}점중 {c_comm_sc}점을 얻어 {calc_pct(c_comm_sc, c_comm_tot)}%'),
        # 반올림 차이 대응 (88% vs 89%)
        (f'{p_comm_tot}점중 {p_comm_sc}점을 얻어 {int(p_comm_sc/p_comm_tot*100)}%',
         f'{c_comm_tot}점중 {c_comm_sc}점을 얻어 {calc_pct(c_comm_sc, c_comm_tot)}%'),

        # "100점중 93점" → "100점중 94점" (전체)
        (f'100점중 {p_overall_pct}점', f'100점중 {c_overall_pct}점'),

        # 진전도 연도 (구체적 문장)
        (f'{by - 1}년도 {pp_overall_pct}%에서 {by}년도 {p_overall_pct}%',
         f'{by}년도 {p_overall_pct}%에서 {ty}년도 {c_overall_pct}%'),

        # === 2. 표 셀 점수 (분수형) ===
        (f'{p_att_sc}/{p_att_tot}', f'{c_att_sc}/{c_att_tot}'),
        (f'{p_comm_sc}/{p_comm_tot}', f'{c_comm_sc}/{c_comm_tot}'),
        (f'{p_total}/{p_all}', f'{c_total}/{p_all}'),

        # === 3. 총점 숫자 ===
        (f'{p_total}점', f'{c_total}점'),

        # === 4. 날짜 (config.json narrative_dates / narrative_dates_dot) ===
        *[(f'{by}년{d}', f'{ty}년{d}') for d in cfg.get('narrative_dates', [])],
        *[(f'{by}.{d}', f'{ty}.{d}') for d in cfg.get('narrative_dates_dot', [])],

        # === 5. 진전도 표 연도 헤더 ===
        (f'{by - 1}년 수행율', f'{by}년 수행율'),

        # === 6. 수행율 % (순서 중요: 구체적→일반적) ===
        # 전체 수행율 93% → 94%
        (f'{p_overall_pct}%', f'{c_overall_pct}%'),
    ]

    return replacements
