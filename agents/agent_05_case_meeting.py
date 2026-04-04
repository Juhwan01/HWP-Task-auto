"""에이전트 05: 사례회의록.

2025 현장평가 데이터를 분석하여 회의내용을 새로 작성한다.
"""
import json
import os
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, load_reference_text, calc_pct, pct_str,
    build_narrative_replacements, parse_ai_blocks, replace_blocks, BASE_DIR,
)

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
    by = cfg['base_year']
    ty = cfg['target_year']
    prev = cfg['scores']['prev_year']
    curr = cfg['scores']['curr_year']
    staff = cfg['staff']

    with open(os.path.join(BASE_DIR, 'extracted_com.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    eval_2025 = data.get(f'2.{ty}년 {cfg["name"]} 현장평가.hwp', '')

    tone_sample = """문체 참고 (이 톤으로 쓰되 문장은 새로):
"-직업훈련교사 고경숙 : 지난 10월 4일 세탁서비스사업부 내부에서 강선미씨에 대한 현장평가를 실시하였습니다."
"-관리부장 김정배 : 강선미씨는 2015년부터 현재까지 세탁물건조 업무를 담당하고 있으며..."
"-사무국장 김남근 : 직업목표로는 세탁직무 수행을 통한 세탁직종의 일반고용 취업과..." """

    prompt = f"""당신은 직업훈련교사 {staff['trainer']}입니다.
{cfg['name']}씨의 {ty}년도 직업재활수립 사례회의록의 회의내용을 작성하세요.

=== {ty}년 현장평가 원본 데이터 (직접 분석하세요) ===
{eval_2025}

=== 전년도({by}년) 점수 ===
작업태도: {prev['attitude'][0]}/{prev['attitude'][1]}, 의사소통: {prev['communication'][0]}/{prev['communication'][1]}
전체: {sum(prev[k][0] for k in ['rules','attitude','communication','skills'])}/{sum(prev[k][1] for k in ['rules','attitude','communication','skills'])}

=== 참석자 ===
원장 {staff['director']}, 사무국장 {staff['secretary']}(사회복지사), 관리부장 {staff['manager']}(사회복지사), 총무대리 {staff['trainer']}(직업훈련교사)

=== {tone_sample} ===

=== 작성 지시 ===
{ty}년 현장평가 데이터를 분석하여 사례회의 내용을 새로 작성하세요.

중요: 이전 회의록을 복사하지 마세요. {ty}년 데이터를 보고 새로운 분석으로 쓰세요.
- 현장평가에서 구체적으로 어떤 항목이 4점이었는지 언급
- {by}년 대비 개선된 점과 여전히 부족한 점을 구분하여 분석
- 발화자별 대화체("-사무국장 김남근 :" 등) 형식 유지
- 각 참석자가 실제 회의에서 할 법한 의견 제시

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
