"""에이전트 공통 베이스 모듈."""
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
                generated[cur_key] = '\n'.join(cur_lines).strip()
            cur_key = match.group(1).strip()
            # 같은 줄에 내용이 이어질 수 있음
            rest = re.sub(r'\[블록[:\s]*[^\]]+\]\s*', '', line).strip()
            cur_lines = [rest] if rest else []
        else:
            cur_lines.append(line)

    if cur_key:
        generated[cur_key] = '\n'.join(cur_lines).strip()

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


def load_reference_text(cfg, key):
    json_path = os.path.join(BASE_DIR, 'extracted_com.json')
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    filename = resolve_path(cfg['templates'][key], cfg)
    return data.get(filename, '')


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

        # === 4. 날짜 ===
        (f'{by}년 10월 04일', f'{ty}년 10월 04일'),
        (f'{by}년 10월 28일', f'{ty}년 10월 28일'),
        (f'{by}년 10월 15일', f'{ty}년 10월 15일'),
        (f'{by}년  10월 15일', f'{ty}년  10월 15일'),
        (f'{by}년  10월  18일', f'{ty}년  10월  18일'),
        (f'{by}.  10.  31.', f'{ty}.  10.  31.'),
        (f'{by}. 10. 04.', f'{ty}. 10. 04.'),
        (f'{by}. 10. 02.', f'{ty}. 10. 02.'),
        (f'{by}.  10.  02.', f'{ty}.  10.  02.'),

        # === 5. 진전도 표 연도 헤더 ===
        (f'{by - 1}년 수행율', f'{by}년 수행율'),

        # === 6. 수행율 % (순서 중요: 구체적→일반적) ===
        # 전체 수행율 93% → 94%
        (f'{p_overall_pct}%', f'{c_overall_pct}%'),
    ]

    return replacements
