"""에이전트 03: 직업재활계획수립상담.

2025 현장평가 데이터를 분석하여 상담내용을 새로 작성한다.
"""
import json
import os
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, load_reference_text, score_summary, pct_str,
    build_narrative_replacements, parse_ai_blocks, replace_blocks, BASE_DIR,
)

OLD_BLOCKS = {
    'consult_content': '-직업재활계획수립을 위한 상담임을 알려주며, 지난 10월 4일 실시한 현장평가에 대한 상담을 진행 함.',
    'consult_result': '-현재 강선미씨는 세탁물건조업무에 만족하고 있으며, 직업유지에 맞춰 목표를 설정   할 필요가 있음.',
    'consult_supervision': '-강선미님의 내성적인 성향으로 대화를 하는 동료들이 많지 않은것 같습니다. 다양한 동료들과 대화를 할수 있도록 관찰 및 지도가 필요합니다.',
}


def run(cfg, hwp, ai):
    src = template_path(cfg, '03_rehab_consult')
    dst = output_path(cfg, '03_rehab_consult')
    by = cfg['base_year']
    ty = cfg['target_year']
    prev = cfg['scores']['prev_year']
    curr = cfg['scores']['curr_year']

    with open(os.path.join(BASE_DIR, 'extracted_com.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    eval_2025 = data.get(f'2.{ty}년 {cfg["name"]} 현장평가.hwp', '')

    ref_text = load_reference_text(cfg, '03_rehab_consult')

    prompt = f"""당신은 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨의 {ty}년도 직업재활계획수립상담 기록을 작성하세요.

=== {ty}년 현장평가 원본 데이터 (직접 분석하세요) ===
{eval_2025}

=== 전년도({by}년) 점수 ===
작업태도: {prev['attitude'][0]}/{prev['attitude'][1]}, 의사소통: {prev['communication'][0]}/{prev['communication'][1]}

=== 문체 참고 (톤만 참고, 문장은 새로) ===
"{ref_text[:200]}"

=== 작성 지시 ===
{ty}년 10월 15일에 진행한 직업재활계획수립상담 내용을 새로 작성하세요.
10월 4일 실시한 현장평가 결과를 바탕으로 상담한 내용입니다.

중요: 이전 상담 기록을 복사하지 마세요. {ty}년 현장평가 데이터를 분석하여 새로 쓰세요.
- 현장평가에서 어떤 항목이 높고 어떤 항목이 낮은지 구체적으로 분석
- {by}년 대비 개선된 점, 여전히 부족한 점 언급
- 상담 분위기와 대상자 반응도 포함

[블록:consult_content] 상담내용 전체 (상담 진행 과정과 현장평가 결과 논의)
[블록:consult_result] 상담결과 및 지원계획
[블록:consult_supervision] 슈퍼비전"""

    result = ai.generate(prompt)

    expected = list(OLD_BLOCKS.keys())
    generated = parse_ai_blocks(result, expected_keys=expected)

    hwp.copy_template_and_open(src, dst)
    hwp.find_replace_many(build_narrative_replacements(cfg))

    failed = replace_blocks(hwp, OLD_BLOCKS, generated, label='수립상담', ai=ai, prompt=prompt)
    if failed:
        print(f'  [경고] 수립상담 교체 실패 블록: {failed}', flush=True)

    hwp.save()
    hwp.close()

    txt_path = txt_output_path(cfg, '03', '직업재활계획수립상담')
    save_txt(txt_path, result)
    return dst


if __name__ == '__main__':
    from core.hwp_engine import HwpEngine
    from core.ai_engine import AiEngine
    cfg = load_config()
    hwp = HwpEngine()
    ai = AiEngine()
    try:
        print(run(cfg, hwp, ai))
    finally:
        hwp.quit()
