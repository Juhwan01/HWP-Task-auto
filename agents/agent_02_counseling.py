"""에이전트 02: 상담기록지.

2025 현장평가 데이터를 바탕으로 연간 상담 내용을 새로 작성한다.
"""
import json
import os
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, load_reference_text, score_summary,
    build_narrative_replacements, parse_ai_blocks, replace_blocks, BASE_DIR,
)

# 2024 원문 — 각 회차별 상담내용/결과/슈퍼비전 블록
OLD_BLOCKS = {
    # === 1회차 (2월) ===
    'counsel_1': '- 강선미님의 고충 및 애로사항을 들어보기 위하여 상담을 진행함.\n\n\n\n- 직장 및 일상생활에서 힘든일이 있거나 궁금한 점은 없는지  물어보자, 특별히 힘    들거나 궁금한 점은 없다고 이야기함.\n\n\n\n- 휴무일에는 뭐하면서 지내냐고 물어보자, TV보면서 지낸다고 얘기하고, 친구들은    안만냐냐고 묻자, 그냥 집에서만 있다고 대답함.\n\n- 집에서 종일 있으면 지루하고 건강에도 좋지 않으니까 가까운 공원에 가서 운동기    구도 타고, 사람들도 보고하면 운동도 되고 머리도 맑아지고 하니까 그것도 좋을     것 같은데 어떠냐고 묻자, 그렇게 해보겠다고 이야기함.\n\n\n\n직장생활이나 일상생활에서 힘든일이 있거나 궁금한 일이 생기면 바로 사무실로 와서 이야기 해달라고 하고 상담을 종료함',
    'result_1': '- 강선미님에게 언제든지 일상생활에서나 직장생활에서나 문제점이 발생하면 사무실    로 알려달라고 함.\n\n- 고충상담직원 및 인권침해 담당자에 대하여 안내함',
    'super_1': '- 휴일에도 집에 있는 것을 좋아해서 회사에서라도 점심 시간등을 이용해\n\n    걷기 운동이라도 할수 있도록 지도 부탁합니다',

    # === 2회차 (5월) ===
    'counsel_2': '- 강선미님의 고충 및 애로사항을 들어보기 위하여 상담을 진행함.\n\n\n\n- 직장 및 일상생활에서 힘든일이 있거나 궁금한 점은 없는지  물어보자, 특별히 힘    들거나 궁금한 점은 없다고 이야기함.\n\n\n\n- 어제 사회적응프로그램으로 세탁사업부 동료들이랑 놀로 갔다 왔는데 괜찮았는지    물어보자, 친구들이랑 기차도 타고 사진도 찍고 맛있는 것도 먹고 해서 너무 좋았    다고 다음에 또 가고 싶다고  이야기함.다음에 프로그램이 있으면 갔이 가자고 하    자 알았다고 꼭 가겠다고 함\n\n\n\n예전에는 너무 말도없고 친구도 많지 않아 걱정을 많이 하였는데 지금은 표현도 하고 동료들이랑 잘 어울려서 너무 좋다고 얘기하자 좋았는지 웃기만 함\n\n\n\n직장생활이나 일상생활에서 힘든일이 있거나 궁금한 일이 생기면 바로 사무실로 와서 이야기 해달라고 하고 상담을 종료함',
    'result_2': '- 강선미님에게 언제든지 일상생활에서나 직장생활에서나 문제점이 발생하면 사무실    로 알려달라고 함.\n\n- 고충상담직원 및 인권침해 담당자에 대하여 안내함',
    'super_2': '- 근로장애인들이 점점 나아짐을 보이고 관계형성에서 즐거움을 보일수 있는 보일 때 마다 걷기 운동이라도 할수 있도록 지도 부탁합니다',

    # === 3회차 (8월) ===
    'counsel_3': '- 강선미씨의 고충 및 궁금사항은 없는지 들어보기 위하여 상담을 진행함.\n\n\n\n- 직장생활을 하면서 힘든점이나 사무실에서 지원해줬으면 하는 것은 없는지    묻자, 그런일은 없다고 대답함.\n\n\n\n- 처음 입사때는 건강관리가 잘됐었는데 체중이 많이 증가해서 이제는 체      중관리를 해야 될 것 같다고 얘기하고, 간호사님이 진행하는 건강관리 프    로그램에 내년 부터는 시작해 보는게 좋겠다고 당부함.\n\n\n\n- 그리고 동료들이랑 얘기할 때 너무작아 잘 들리지가 않는데 목소리를 조금    더 높여 보는것도 좋을 것 같다고 얘기함.\n\n\n\n- 직장생활을 하면서 사소한 문제라도 생기거나 궁금한 점이 발생하면 바로    사무실로 와서 이야기 해달라고 하고 상담을 종료함',
    'result_3': '- 체중관리가 잘되지 않아 내년부터는 건강관리 프로그램에 참여할수 있도록    독려할 계획임.',
    'super_3': '- 강선미님이 체중관리가 필요합니다. 건강관리 프로그램에 참여할수 있도록       독려해 주시고, 동료들이랑 같이 하는 자리를 자주 마련하여 자신있게\n\n    목소리를 낼수 있도록 격려가 지도가 필요함..',
}


def run(cfg, hwp, ai):
    src = template_path(cfg, '02_counseling')
    dst = output_path(cfg, '02_counseling')
    by = cfg['base_year']
    ty = cfg['target_year']
    dates = cfg['counseling_dates']

    with open(os.path.join(BASE_DIR, 'extracted_com.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    eval_2025 = data.get(f'2.{ty}년 {cfg["name"]} 현장평가.hwp', '')

    ref_text = load_reference_text(cfg, '02_counseling')

    prompt = f"""당신은 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨({cfg['disability']}, {cfg['department']} {cfg['job']})의 {ty}년도 상담기록지를 작성하세요.

=== {ty}년 현장평가 데이터 (참고) ===
{eval_2025[:800]}

=== {ty}년 상담 일정 ===
1회차: {dates[0]['date']} ({dates[0]['time']}), {dates[0]['purpose']}
2회차: {dates[1]['date']} ({dates[1]['time']}), {dates[1]['purpose']}
3회차: {dates[2]['date']} ({dates[2]['time']}), {dates[2]['purpose']}

=== 대상자 배경 ===
- {cfg['name']}, {cfg['disability']}, {cfg['birth_date']}생
- {cfg['department']}에서 {cfg['job']} 업무 담당
- 내성적인 성격, 의사표현에 어려움
- 부모님, 오빠와 거주
- 2024년 8월 상담에서 체중관리 프로그램 참여 권유받음

=== 문체 참고 (톤만 참고, 내용은 새로) ===
아래는 {by}년 상담기록 중 일부입니다. 이런 톤으로 쓰되 내용은 {ty}년 상황에 맞게 새로 쓰세요:
"{ref_text[:400]}"

=== 작성 지시 ===
{ty}년도 3회분 상담을 각각 새로 작성하세요. 각 회차마다 다른 상담 주제와 상황을 담아주세요.

중요:
- 이전 상담 기록을 복사하지 마세요
- 각 회차마다 고유한 대화 내용과 상황이 있어야 합니다
- 1회차(2월): 연초 근황 확인, 새해 목표 등
- 2회차(5월): 중간 점검, 동료관계, 직장생활
- 3회차(8월): 하반기 점검, 현장평가 대비

각 블록별로 출력하세요:

[블록:counsel_1] 1회차 상담내용 (구체적 대화 묘사)
[블록:result_1] 1회차 상담결과 및 지원계획
[블록:super_1] 1회차 슈퍼비전 (상급자 소견, 1~2문장)

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
