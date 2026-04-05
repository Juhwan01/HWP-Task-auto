"""에이전트 05: 사례회의록.

2025 현장평가 파싱 데이터를 기반으로 회의내용을 새로 작성한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
)
from core.eval_parser import load_eval_parsed, format_for_prompt, compare_years

OLD_BLOCKS = {
    'meeting_eval': '-직업훈련교사 고경숙 : 현장평가 결과 강선미씨의 경우 전체 평균 수행점수 100점중 93점의 높은 점수를 받았습니다.각 영역별로 살펴보면 작업규칙영역에서 총점 50점중 50점을 얻어 100%의 높은 수행율을 보였고,작업태도영역에서 총점 110점중 100점을 얻어 91%의 수행율을 보였습니다.의사소통 및 대인관계영역에서는 90점중 80점을 얻어 88%의 수행율을 보였고, 직무기술영역에서 총점 40점중 40점을 얻어 100%의 수행율을 보였습니다.이와 같이 영역별 수행율을 종합적으로 살펴보면 작업규칙,직무기술영역에서는 100%의 높은 수행율을 보였으며, 작업태도,의사소통 및 대인관계영역에서는 다른 영역보다 낮은 수행율을 보였습니다.',
    'meeting_focus': '강선미씨의 경우 직무기술 분야중 세탁물건조 업무를 계속 수행해 왔기 때문에 수행율이 높게 나옴. 따라서 현재 배치된 직무기술과 관련해서는 이미 잘수행하고 있기 때문에 직무기술의 향상 보다는 근로장애인으로서의 직업유지에 초점을 맞춰 목표를 설정하고자 합니다.',
    'meeting_issue': '의사소통/대인관계 영역에서 전년도와 마찬가지로 내성적인 성격으로 인해 어려운 일에 처했을 때 관리자나 동료에게 도움을 요청해야 하는데 그렇치 못했으며, 이런 이유로 인해 본인의 의사를 분명하게 얘기하지 못하는 모습들이 보여, 향후 직업재활계획수립시 문제점을 보였던 의사소통 및 대인관계영역 개선을 전년도에 이어 장기목표로 설정하는것이 필요하다고 생각합니다.',
    'meeting_progress': '-직업훈련교사 고경숙 : 진전도 평가결과 강선미씨의 경우 영역별로 살펴보면 작업태도,의사소통 및 대인관계영역에서 1%의 소폭증가를 보였고, 작업규칙,직무기술영역에서는 전년도와 동일한 수행율을 보였음.',
    'meeting_progress_overall': '종합적으로 살펴보면 2023년도 92%에서 2024년도 93%의 소폭상승을 보이기는 했지만 전체적으로 높은 수행율을 보인만큼  수행율 상승보다 지속적인 유지를 위해 작업에 집중할수 있도록 관심과 관찰이 필요하다고 생각됩니다.',
    'meeting_goal': '-사무국장 김남근 : 김정배 관리부장님의 의견과 강선미씨의 현장평가 결과를 반영하여, 세탁물건조업무를 계속 수행하여도 될것으로 사료되며, 직업목표로는 세탁직무 수행을 통한 세탁직종의 일반고용 취업과 희망직무의 직업유지와 장기목표는 의사소통 및 대인관계영역의 향상을 단기목표로는 어려운 일에 처했을 때 관리자와 동료에게 도움을 청한다 3점에서 4점으로 향상,본인의 의사를 분명하고 적절하게 표현한다 3점에서 4점으로 향상, 2가지를  단기목표로 설정하여 직업재활계획서를 수립하자고 함.',
}


def run(cfg, hwp, ai):
    src = template_path(cfg, '05_case_meeting')
    dst = output_path(cfg, '05_case_meeting')
    ty = cfg['target_year']
    by = cfg['base_year']
    staff = cfg['staff']

    # 파서로 팩트 추출
    parsed_curr = load_eval_parsed(ty)
    parsed_prev = load_eval_parsed(by)
    facts = format_for_prompt(parsed_curr)
    changes = compare_years(parsed_prev, parsed_curr) if parsed_prev else ''

    # 의사소통 약점 항목 추출 (단기목표 설정용)
    comm_section = parsed_curr['sections'].get('의사소통', {})
    weak_items = [it for it in comm_section.get('items', []) if it['score'] <= 3]
    weak_detail = ', '.join(f"'{it['text']}' ({it['score']}점)" for it in weak_items)

    prompt = f"""당신은 직업훈련교사 {staff['trainer']}입니다.
{cfg['name']}씨의 {ty}년도 직업재활수립 사례회의록의 회의내용을 작성하세요.

=== {ty}년 현장평가 팩트 (이 데이터만 근거로 쓰세요) ===
{facts}

=== 전년도({by}년) 대비 변화 ===
{changes}

=== 의사소통 약점 항목 (단기목표 후보) ===
{weak_detail or '(3점 이하 없음)'}

=== 참석자 ===
- 원장 {staff['director']}
- 사무국장 {staff['secretary']} (사회복지사)
- 관리부장 {staff['manager']} (사회복지사)
- 직업훈련교사 {staff['trainer']} (사례관리자)

=== 대상자 배경 ===
- {cfg['disability']}, {cfg['department']} {cfg['job']} 담당
- {cfg.get('hire_year', 2015)}년 입사
- 직업목표: {cfg.get('career_goal', '세탁직종 일반고용 취업')}
- 장기목표: {cfg['long_term_goal']}
- 단기목표: {', '.join(cfg['short_term_goals'])}

=== 문체 규칙 ===
- 발화체: "-직업훈련교사 {staff['trainer']} :" 형식으로 시작
- 존대어미: "~합니다", "~입니다", "~보였습니다"
- 사무국장 발언(meeting_goal)만 "~함", "~사료됨" 혼용 가능
- 점수 표기: "총점 90점중 82점을 얻어 91%의 수행율" 형식

=== 작성 지시 ===
현장평가 팩트를 근거로 사례회의 내용을 새로 작성하세요.

회의 흐름:
1. {staff['trainer']} 교사가 현장평가 결과를 영역별로 상세 보고
2. {staff['trainer']} 교사가 직무기술 높으므로 직업유지 초점 방향 제시
3. {staff['trainer']} 교사가 의사소통 영역 약점 구체적 분석
4. {staff['trainer']} 교사가 진전도(전년도 대비) 보고
5. 종합 분석
6. {staff['secretary']} 사무국장이 최종 목표 설정 (직업목표, 장단기목표, 단기목표 점수 향상 목표)

[블록:meeting_eval] {staff['trainer']} 교사의 현장평가 결과 상세 보고
[블록:meeting_focus] {staff['trainer']} 교사의 목표 방향 제시
[블록:meeting_issue] {staff['trainer']} 교사의 의사소통/대인관계 문제점 분석
[블록:meeting_progress] {staff['trainer']} 교사의 진전도 보고
[블록:meeting_progress_overall] 종합 분석
[블록:meeting_goal] {staff['secretary']} 사무국장의 최종 목표 설정"""

    result = ai.generate(prompt)

    expected = list(OLD_BLOCKS.keys())
    generated = parse_ai_blocks(result, expected_keys=expected)

    hwp.copy_template_and_open(src, dst)
    hwp.find_replace_many(build_narrative_replacements(cfg))

    failed = replace_blocks(hwp, OLD_BLOCKS, generated, label='사례회의록', ai=ai, prompt=prompt)
    if failed:
        print(f'  [경고] 사례회의록 교체 실패 블록: {failed}', flush=True)

    hwp.save()
    hwp.close()

    txt_path = txt_output_path(cfg, '05', '사례회의록')
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
