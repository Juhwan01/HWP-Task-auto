"""에이전트 04: 직업평가보고서.

2025 현장평가 데이터를 직접 분석하여 서술을 새로 작성한다.
2024 문서는 문체/톤 참고용으로만 사용.
"""
import json
import os
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, load_reference_text, calc_pct, pct_str,
    build_narrative_replacements, parse_ai_blocks, replace_blocks, BASE_DIR,
)

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


def _load_eval_2025(cfg):
    """2025 현장평가 텍스트 로드."""
    with open(os.path.join(BASE_DIR, 'extracted_com.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get(f'2.{cfg["target_year"]}년 {cfg["name"]} 현장평가.hwp', '')


def run(cfg, hwp, ai):
    src = template_path(cfg, '04_eval_report')
    dst = output_path(cfg, '04_eval_report')
    by = cfg['base_year']
    ty = cfg['target_year']
    prev = cfg['scores']['prev_year']
    curr = cfg['scores']['curr_year']

    eval_2025 = _load_eval_2025(cfg)

    # 톤 참고용 샘플 (짧게만)
    tone_sample = """다음은 이전 보고서의 문체 예시입니다. 이 톤(~함, ~보임, ~있음 등)으로 쓰되 문장 자체는 새로 쓰세요:
"현장평가 결과 강선미씨의 경우 전체 평균 수행점수 100점중 93점의 높은 점수를 받았음."
"강선미씨의 경우 직무기술 분야중 세탁물 건조 업무를 계속 수행해 왔기 때문에 수행율이 높게 나옴."
"향후 직업재활계획수립시 문제점을 보였던 의사소통 및 대인관계 영역 개선을 장기목표로 설정할 필요가 있음." """

    prompt = f"""당신은 장애인 직업재활시설의 직업훈련교사 {cfg['case_manager']}입니다.
{cfg['name']}씨({cfg['disability']}, {cfg['department']} {cfg['job']})의 {ty}년도 직업평가보고서 서술 부분을 작성하세요.

=== {ty}년 현장평가 원본 데이터 (이것을 직접 분석하세요) ===
{eval_2025}

=== 전년도({by}년) 점수 (비교용) ===
작업규칙: {prev['rules'][0]}/{prev['rules'][1]}, 작업태도: {prev['attitude'][0]}/{prev['attitude'][1]}, 의사소통/대인관계: {prev['communication'][0]}/{prev['communication'][1]}, 직무기술: {prev['skills'][0]}/{prev['skills'][1]}

=== {tone_sample} ===

=== 작성 지시 ===
위 {ty}년 현장평가 데이터를 직접 분석하여 아래 7개 블록을 작성하세요.

중요: 2024년 보고서를 복사하지 마세요. {ty}년 데이터를 보고 새로 분석하여 쓰세요.
- {ty}년 결과에서 어떤 항목이 5점(만점)이고 어떤 항목이 4점/3점인지 구체적으로 분석
- {by}년 대비 어떤 영역이 개선/유지/하락했는지 해석
- 개선된 부분은 긍정적으로 언급하고, 여전히 부족한 부분은 지속 관리 필요성 서술
- 문체만 위 톤 참고 예시를 따르고, 문장 구조와 내용은 새로 쓰세요

[블록:eval_narrative] 현장평가 결과 분석 서술 (영역별 점수와 특징)
[블록:eval_analysis] 직무기술 분석 및 향후 목표 방향 설정
[블록:eval_issue] 의사소통/대인관계 영역의 구체적 문제점과 개선 필요성
[블록:eval_shortgoal] 장기목표 기반 단기목표 설정
[블록:progress_detail] 진전도 평가 (영역별 전년도 대비 변화 분석)
[블록:progress_overall] 진전도 종합 분석 (개선점과 지속 과제)
[블록:progress_summary] 전체 연도간 비교 종합 정리"""

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
