"""에이전트 03: 직업재활계획수립상담.

현장평가 파싱 데이터를 기반으로 상담내용을 새로 작성한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
    load_eval_facts, enrich_cfg_from_eval, load_old_blocks,
)

OLD_BLOCKS = load_old_blocks('agent_03')


def run(cfg, hwp, ai):
    src = template_path(cfg, '03_rehab_consult')
    dst = output_path(cfg, '03_rehab_consult')
    ty = cfg['target_year']
    by = cfg['base_year']

    cfg = enrich_cfg_from_eval(cfg)
    ef = load_eval_facts(cfg)
    facts = ef['facts']
    changes = ef['changes']

    prompt = f"""당신은 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨의 {ty}년도 직업재활계획수립상담 기록을 작성하세요.

=== {ty}년 현장평가 팩트 (이 데이터만 근거로 쓰세요) ===
{facts}

=== 전년도({by}년) 대비 변화 ===
{changes}

=== 대상자 배경 ===
- {cfg['disability']}, {cfg['department']} {cfg['job']} 담당
- {cfg.get('hire_year', 2015)}년 입사, 현재까지 동일 직무 수행
- 장기목표: {cfg['long_term_goal']}
- 단기목표: {', '.join(cfg['short_term_goals'])}

=== 문체 규칙 ===
- 상담내용/결과: "~함", "~보임", "~있음" 등 보고서체
- 슈퍼비전: "~합니다", "~필요합니다" 등 존대체
- 점수 표기: "90점중 82점을 얻어 91%" 형식

=== 작성 지시 ===
{ty}년 10월 15일에 진행한 직업재활계획수립상담입니다.
10월 4일 실시한 현장평가 결과를 바탕으로 상담한 내용입니다.

- 현장평가에서 5점(강점) 항목과 4점/3점(개선필요) 항목을 구체적으로 언급
- 전년도 대비 개선된 점(의사소통 +2점 등)과 여전히 부족한 점 서술
- 직무기술은 이미 높으므로 직업유지에 초점을 맞춘 목표 설정 방향 제시
- 상담 분위기와 대상자 반응도 자연스럽게 포함

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
