"""에이전트 02: 상담기록지.

전년도 현장평가 파싱 데이터를 바탕으로 연간 상담 내용을 새로 작성한다.
상담 시점(2/5/8월)은 현장평가(10월) 이전이므로 전년도 평가 결과를 참고한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
    load_eval_facts, enrich_cfg_from_eval, load_old_blocks,
)

OLD_BLOCKS = load_old_blocks('agent_02')


def run(cfg, hwp, ai):
    src = template_path(cfg, '02_counseling')
    dst = output_path(cfg, '02_counseling')
    by = cfg['base_year']
    ty = cfg['target_year']
    dates = cfg['counseling_dates']

    cfg = enrich_cfg_from_eval(cfg)

    # 전년도 평가 결과 로드 (상담은 평가 전이므로 전년도 기준)
    ef = load_eval_facts(cfg, mode='prev_only')
    prev_facts = ef['facts']
    weak_detail = ef['weak_detail']
    moderate_detail = ef['moderate_detail']

    prompt = f"""당신은 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨({cfg['disability']}, {cfg['department']} {cfg['job']})의 {ty}년도 상담기록지를 작성하세요.

=== 전년도({by}년) 현장평가 팩트 (상담 시 참고 가능한 데이터) ===
{prev_facts}

=== 의사소통 영역 상세 (상담 주제 활용) ===
약점(3점 이하):
{weak_detail or '  (없음)'}
보통(4점, 개선 가능):
{moderate_detail or '  (없음)'}

=== {ty}년 상담 일정 ===
1회차: {dates[0]['date']} ({dates[0]['time']}), {dates[0]['purpose']}
2회차: {dates[1]['date']} ({dates[1]['time']}), {dates[1]['purpose']}
3회차: {dates[2]['date']} ({dates[2]['time']}), {dates[2]['purpose']}

=== 대상자 배경 ===
- {cfg['name']}, {cfg['disability']}, {cfg['birth_date']}생
- {cfg['department']}에서 {cfg['job']} 업무 담당, {cfg.get('hire_year', 2015)}년 입사
- 내성적인 성격, 의사표현에 어려움
- 장기목표: {cfg['long_term_goal']}
- 단기목표: {', '.join(cfg['short_term_goals'])}

=== 문체 규칙 ===
- 상담내용: 대화체 묘사 ("~묻자, ~라고 대답함", "~얘기하자, ~라고 함")
- 상담결과: 보고서체 ("~계획임", "~안내함")
- 슈퍼비전: 존대체 ("~필요합니다", "~부탁합니다")

=== 구체적 일상 디테일 작성법 (필수) ===
상담기록은 추상적이면 안 됩니다. 아래처럼 구체적인 일상 디테일을 반드시 포함하세요.

좋은 예시 (구체적):
- "휴무일에는 뭐하면서 지내냐고 물어보자, TV보면서 지낸다고 얘기함"
- "친구들은 안만냐냐고 묻자, 그냥 집에서만 있다고 대답함"
- "가까운 공원에 가서 운동기구도 타고 사람들도 보면 운동도 되고 머리도 맑아지고 하니까 어떠냐고 묻자, 그렇게 해보겠다고 이야기함"
- "어제 사회적응프로그램으로 세탁사업부 동료들이랑 놀로 갔다 왔는데 괜찮았는지 물어보자, 기차도 타고 사진도 찍고 맛있는 것도 먹고 해서 너무 좋았다고 함"
- "체중이 많이 증가해서 체중관리를 해야 될 것 같다고 얘기하고, 간호사님이 진행하는 건강관리 프로그램에 참여해 보는게 좋겠다고 당부함"

나쁜 예시 (추상적, 금지):
- "일상생활에 대해 이야기를 나눔" ← 구체적 내용 없음
- "동료관계에 대해 상담함" ← 누구와 무슨 일이 있었는지 없음
- "건강관리를 권유함" ← 구체적 방법 없음

규칙: 각 회차마다 최소 3가지 이상의 구체적 대화 장면(질문→대답→반응)을 포함하세요.

=== 작성 지시 ===
{ty}년도 3회분 상담을 각각 새로 작성하세요.

주의:
- 상담 시점은 현장평가(10월) 이전입니다. {by}년 평가 결과를 바탕으로 상담합니다.
- 각 회차마다 고유한 대화 내용과 상황이 있어야 합니다
- 1회차({dates[0]['date'][:7]}): 연초 고충상담, 근황 확인, 새해 생활 점검 (설 연휴 어떻게 보냈는지, 휴일 생활습관, 운동 여부 등)
- 2회차({dates[1]['date'][:7]}): 고충상담, 동료관계·직장생활 점검 (최근 사회적응프로그램·동료 활동, 의사소통 향상 격려)
- 3회차({dates[2]['date'][:7]}): 사례관리, {by}년 평가에서 약점이었던 의사소통 항목 개선 여부 점검, 건강관리, 10월 현장평가 대비

[블록:counsel_1] 1회차 상담내용 (구체적 대화 묘사)
[블록:result_1] 1회차 상담결과 및 지원계획
[블록:super_1] 1회차 슈퍼비전 (1~2문장)

[블록:counsel_2] 2회차 상담내용
[블록:result_2] 2회차 상담결과 및 지원계획
[블록:super_2] 2회차 슈퍼비전

[블록:counsel_3] 3회차 상담내용
[블록:result_3] 3회차 상담결과 및 지원계획
[블록:super_3] 3회차 슈퍼비전"""

    result = ai.generate(prompt)

    expected = list(OLD_BLOCKS.keys())
    generated = parse_ai_blocks(result, expected_keys=expected)

    hwp.copy_template_and_open(src, dst)
    hwp.find_replace_many(build_narrative_replacements(cfg))

    # 상담 날짜 교체
    prev_dates = [f'{by}년 2월 19일', f'{by}년 5월 23일', f'{by}년  8월  13일']
    new_dates = [dates[0]['date'], dates[1]['date'], dates[2]['date']]
    hwp.find_replace_many(list(zip(prev_dates, new_dates)))

    # AI 생성 내용을 HWP에 삽입
    failed = replace_blocks(hwp, OLD_BLOCKS, generated, label='상담기록지', ai=ai, prompt=prompt)
    if failed:
        print(f'  [경고] 상담기록지 교체 실패 블록: {failed}', flush=True)

    hwp.save()
    hwp.close()

    txt_path = txt_output_path(cfg, '02', '상담기록지')
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
