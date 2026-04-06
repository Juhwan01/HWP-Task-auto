"""에이전트 04: 직업평가보고서.

현장평가 파싱 데이터를 기반으로 서술을 새로 작성한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
    load_eval_facts, enrich_cfg_from_eval, load_old_blocks,
)

OLD_BLOCKS = load_old_blocks('agent_04')


def run(cfg, hwp, ai):
    src = template_path(cfg, '04_eval_report')
    dst = output_path(cfg, '04_eval_report')
    ty = cfg['target_year']
    by = cfg['base_year']

    cfg = enrich_cfg_from_eval(cfg)
    ef = load_eval_facts(cfg)
    facts = ef['facts']
    changes = ef['changes']
    weak_detail = ef['weak_detail']
    moderate_detail = ef['moderate_detail']

    prompt = f"""당신은 장애인 직업재활시설의 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨({cfg['disability']}, {cfg['department']} {cfg['job']})의 {ty}년도 직업평가보고서 서술 부분을 작성하세요.

=== {ty}년 현장평가 팩트 (이 데이터만 근거로 쓰세요) ===
{facts}

=== 전년도({by}년) 대비 변화 ===
{changes}

=== 의사소통 영역 상세 ===
약점(3점 이하):
{weak_detail or '  (없음)'}
보통(4점):
{moderate_detail or '  (없음)'}

=== 대상자 배경 ===
- {cfg.get('hire_year', 2015)}년 입사, {cfg['job']} 직무 계속 수행
- 장기목표: {cfg['long_term_goal']}
- 단기목표: {', '.join(cfg['short_term_goals'])}

=== 문체 규칙 ===
- 보고서체: "~함", "~보임", "~있음", "~사료됨" 등
- 점수 표기: "총점 90점중 82점을 얻어 91%의 수행율을 보임" 형식
- 전체 평균: "100점중 94점" 형식 (총점/총만점을 100점 기준으로 환산)

=== 작성 지시 ===
아래 7개 블록을 현장평가 팩트에 근거하여 새로 작성하세요.
- 각 영역의 점수와 수행율을 정확히 인용
- 어떤 항목이 만점(5점)이고 어떤 항목이 4점/3점인지 구체적으로 분석
- 전년도 대비 개선/유지/하락 영역을 명확히 구분
- 직무기술은 높으므로 직업유지 초점의 목표 설정 방향 제시
- 의사소통 약점 항목(3점)을 구체적으로 언급하며 개선 필요성 서술

[블록:eval_narrative] 현장평가 결과 분석 서술 (영역별 점수와 수행율)
[블록:eval_analysis] 직무기술 분석 및 목표 방향 설정
[블록:eval_issue] 의사소통/대인관계 영역 문제점과 개선 필요성
[블록:eval_shortgoal] 장기목표 기반 단기목표 설정
[블록:progress_detail] 진전도 평가 (영역별 전년도 대비 변화)
[블록:progress_overall] 진전도 종합 분석 (개선점과 지속 과제)
[블록:progress_summary] 전체 연도간 비교 종합 정리 ({by}년 {ef['prev_total_pct']}%에서 {ty}년 {ef['curr_total_pct']}%)"""

    result = ai.generate(prompt)

    expected = list(OLD_BLOCKS.keys())
    generated = parse_ai_blocks(result, expected_keys=expected)

    hwp.copy_template_and_open(src, dst)

    # 1. 표 점수/날짜 교체
    hwp.find_replace_many(build_narrative_replacements(cfg))

    # 2. 서술 블록을 AI 새 내용으로 교체
    failed = replace_blocks(hwp, OLD_BLOCKS, generated, label='평가보고서', ai=ai, prompt=prompt)
    if failed:
        print(f'  [경고] 평가보고서 교체 실패 블록: {failed}', flush=True)

    hwp.save()
    hwp.close()

    txt_path = txt_output_path(cfg, '04', '직업평가보고서')
    save_txt(txt_path, result)
    return dst


if __name__ == '__main__':
    from agents.base import run_standalone
    run_standalone(run, needs_ai=True)
