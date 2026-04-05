"""에이전트 04: 직업평가보고서.

2025 현장평가 파싱 데이터를 기반으로 서술을 새로 작성한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
)
from core.eval_parser import load_eval_parsed, format_for_prompt, compare_years

# 2024 원문 (find_replace 대상)
OLD_BLOCKS = {
    'eval_narrative': '현장평가 결과 강선미씨의 경우 전체 평균 수행점수 100점중 93점의 높은 점수를 받았음. 영역별로 살펴보면 작업규칙영역에서 총점 50점중 50점을 얻어 100% 높은 수행율을 보였고, 작업태도영역에서 총점 110점중 100점을 얻어 91%수행율을 보임. 의사소통 및 대인관계영역에서는 총점 90점중 80점을 얻어 89%의 수행율을 보였고, 직무기술영역에서는 총점 40점중 40점을 얻어 100%의수행율을 보임.이와 같이 영역별 수행율을 종합적으로 살펴보면 작업규칙,직무기술영역에서는 100%의 높은 수행율을 보였으며 작업태도,의사소통 및 대인관계영역에서는 다른 영역보다 낮은 수행율을 보임.',
    'eval_analysis': '강선미씨의 경우 직무기술 분야중 세탁물 건조 업무를 계속 수행해 왔기 때문에 수행율이 높게 나옴. 따라서 현재 배치된 직무기숙과 관련해서는 이미 잘 수행하고 있기 때문에 직무기술의 향상 보다 근로장애인으로서의 직업유지에 초점을 맞춰 목표를 설정하고자 함.',
    'eval_issue': '의사소통 및 대인관계 영역에서는 전년도와 마찬가지로 내성적인 성격으로 인해 어려운 일에 처했을 때 관리자나 동료에게 도움을 요청해야 하는데 그렇치 못했으며, 이런 성향으로 인해 본인의 의사를 분명하게 얘기하지 못하는 모습들이 개선이 필요하다고 보여, 향후 직업재활계획수립시 문제점을 보였던 의사소통 및 대인관계 영역 개선을 전년도에 이어 장기목표로 설정할 필요가 있음.',
    'eval_shortgoal': '위의 장기목표를 바탕으로 하여 1.어려운 일에 처했을 때 관리자와 동료에게 도움을 구한다. 2.본인의 의사를 분명하고 적절하게 표현한다 위 2가지를 단기목표로 설정할 필요가 있음.',
    'progress_detail': '진전도 평가결과 강선미씨의 경우 영역별로 살펴보면 작업태도 영역,의사소통 및 대인관계영역에서 1%의 소폭증가를 보였고, 작업규칙,직무기술영역에서는 전년도와 동일한 수행율을 보였음.',
    'progress_overall': '작업규칙,작업태도,직무기술영역에서 90%이상의 높은 수행율을 유지하고 있어 문제점은 보이지 않았지만, 높은 수행율을 유지하고는 있지만 전년도에 이어 문제점을 보였던 의사소통 및 대인관계 영역의 개선이 필요하다고 보여 장.단기 목표를 설정해 서비스 제공이 되어야 된다고 생각됨.',
    'progress_summary': '종합적으로 살펴보면 2023년도 92%에서 2024년도 93%의 소폭상승을 보이기는 했지만 전체적으로 높은 수행율을 보인만큼 수행율 상승보다 지속적인 유지를 위해 작업에 집중할수 있도록 관심과 관찰이 필요하다고 사료됨.',
}


def run(cfg, hwp, ai):
    src = template_path(cfg, '04_eval_report')
    dst = output_path(cfg, '04_eval_report')
    ty = cfg['target_year']
    by = cfg['base_year']

    # 파서로 팩트 추출
    parsed_curr = load_eval_parsed(ty)
    parsed_prev = load_eval_parsed(by)
    facts = format_for_prompt(parsed_curr)
    changes = compare_years(parsed_prev, parsed_curr) if parsed_prev else ''

    # 의사소통 영역 약점 항목 상세 추출
    comm_section = parsed_curr['sections'].get('의사소통', {})
    weak_items = [it for it in comm_section.get('items', []) if it['score'] <= 3]
    moderate_items = [it for it in comm_section.get('items', []) if it['score'] == 4]
    weak_detail = '\n'.join(f"  - {it['text']} ({it['score']}점)" for it in weak_items)
    moderate_detail = '\n'.join(f"  - {it['text']} (4점)" for it in moderate_items)

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
[블록:progress_summary] 전체 연도간 비교 종합 정리 ({by}년 {parsed_prev['summary']['total_pct'] if parsed_prev else 'N/A'}%에서 {ty}년 {parsed_curr['summary']['total_pct']}%)"""

    result = ai.generate(prompt)

    expected = list(OLD_BLOCKS.keys())
    generated = parse_ai_blocks(result, expected_keys=expected)

    hwp.copy_template_and_open(src, dst)

    # 1. 표 점수/날짜 교체
    hwp.find_replace_many(build_narrative_replacements(cfg))

    # 2. 서술 블록을 AI 새 내용으로 교체
    failed = replace_blocks(hwp, OLD_BLOCKS, generated, label='평가보고서')
    if failed:
        print(f'  [경고] 평가보고서 교체 실패 블록: {failed}', flush=True)

    hwp.save()
    hwp.close()

    txt_path = txt_output_path(cfg, '04', '직업평가보고서')
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
