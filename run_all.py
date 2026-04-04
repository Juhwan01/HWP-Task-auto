"""전체 문서 생성 오케스트레이터.

사용법:
    python run_all.py              # 전체 6개 문서 생성
    python run_all.py 1 4          # 1번, 4번 문서만 생성
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.base import load_config
from core.hwp_engine import HwpEngine
from core.ai_engine import AiEngine
from agents import (
    agent_01_eval_plan,
    agent_02_counseling,
    agent_03_rehab_consult,
    agent_04_eval_report,
    agent_05_case_meeting,
    agent_06_rehab_plan,
)

AGENTS = {
    1: ('직업평가계획서', agent_01_eval_plan, False),
    2: ('상담기록지', agent_02_counseling, True),
    3: ('직업재활계획수립상담', agent_03_rehab_consult, True),
    4: ('직업평가보고서', agent_04_eval_report, True),
    5: ('사례회의록', agent_05_case_meeting, True),
    6: ('직업재활계획서', agent_06_rehab_plan, False),
}


def main():
    # 실행할 에이전트 번호 결정
    if len(sys.argv) > 1:
        nums = [int(x) for x in sys.argv[1:]]
    else:
        nums = list(AGENTS.keys())

    cfg = load_config()
    print(f'=== {cfg["target_year"]}년도 {cfg["name"]} 문서 생성 ===', flush=True)
    print(f'대상 에이전트: {nums}', flush=True)

    hwp = HwpEngine()
    ai = AiEngine() if any(AGENTS[n][2] for n in nums) else None
    print('엔진 초기화 완료\n', flush=True)

    results = {}
    for num in nums:
        label, agent, needs_ai = AGENTS[num]
        print(f'[{num}/6] {label} ...', end=' ', flush=True)
        start = time.time()
        try:
            path = agent.run(cfg, hwp, ai if needs_ai else None)
            elapsed = time.time() - start
            results[num] = ('OK', path)
            print(f'완료 ({elapsed:.1f}s)', flush=True)
        except Exception as e:
            elapsed = time.time() - start
            results[num] = ('FAIL', str(e))
            print(f'실패 ({elapsed:.1f}s): {e}', flush=True)

    hwp.quit()

    print(f'\n=== 결과 ===', flush=True)
    ok = sum(1 for s, _ in results.values() if s == 'OK')
    print(f'{ok}/{len(nums)} 성공', flush=True)
    for num in nums:
        status, detail = results[num]
        label = AGENTS[num][0]
        icon = 'O' if status == 'OK' else 'X'
        print(f'  [{icon}] {num}. {label}: {detail}', flush=True)

    if ai:
        print(f'\n[참고] AI 생성 서술은 output/_*.txt 파일을 확인하세요.', flush=True)


if __name__ == '__main__':
    main()
