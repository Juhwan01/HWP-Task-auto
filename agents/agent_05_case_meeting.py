"""에이전트 05: 사례회의록.

현장평가 파싱 데이터를 기반으로 회의내용을 새로 작성한다.
Data-Grounded Generation: 팩트만 전달, 원문 없음.
"""
from agents.base import (
    load_config, template_path, output_path, txt_output_path,
    save_txt, build_narrative_replacements, parse_ai_blocks, replace_blocks,
    load_eval_facts, enrich_cfg_from_eval, load_old_blocks,
)

OLD_BLOCKS = load_old_blocks('agent_05')


def run(cfg, hwp, ai):
    src = template_path(cfg, '05_case_meeting')
    dst = output_path(cfg, '05_case_meeting')
    ty = cfg['target_year']
    by = cfg['base_year']
    staff = cfg['staff']

    cfg = enrich_cfg_from_eval(cfg)
    ef = load_eval_facts(cfg)
    facts = ef['facts']
    changes = ef['changes']
    weak_detail = ', '.join(f"'{it['text']}' ({it['score']}점)" for it in ef['weak_items'])

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

중요: [블록:키] 태그 안에 화자 접두어까지 포함하세요. 태그 앞에 화자를 쓰지 마세요.
예시:
[블록:meeting_eval]
-직업훈련교사 {staff['trainer']} : 내용...

[블록:meeting_eval] -직업훈련교사 {staff['trainer']} : 현장평가 결과 상세 보고
[블록:meeting_focus] -직업훈련교사 {staff['trainer']} : 목표 방향 제시
[블록:meeting_issue] -직업훈련교사 {staff['trainer']} : 의사소통/대인관계 문제점 분석
[블록:meeting_progress] -직업훈련교사 {staff['trainer']} : 진전도 보고
[블록:meeting_progress_overall] 종합 분석
[블록:meeting_goal] -{staff['secretary']} 사무국장 : 최종 목표 설정"""

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
    from agents.base import run_standalone
    run_standalone(run, needs_ai=True)
