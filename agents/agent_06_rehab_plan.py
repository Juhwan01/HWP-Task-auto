"""에이전트 06: 직업재활계획서 (FindReplace only)."""
from agents.base import (
    load_config, template_path, output_path, calc_pct, pct_str,
    build_narrative_replacements, enrich_cfg_from_eval,
)


def run(cfg, hwp, ai=None):
    src = template_path(cfg, '06_rehab_plan')
    dst = output_path(cfg, '06_rehab_plan')

    cfg = enrich_cfg_from_eval(cfg)
    by = cfg['base_year']
    ty = cfg['target_year']
    ny = ty + 1

    prev_comm = cfg['scores']['prev_year']['communication']
    curr_comm = cfg['scores']['curr_year']['communication']
    prev_pct = pct_str(prev_comm[0], prev_comm[1])
    curr_pct = pct_str(curr_comm[0], curr_comm[1])
    curr_pct_num = calc_pct(curr_comm[0], curr_comm[1])
    next_pct = f'{curr_pct_num + 2}%'

    hwp.copy_template_and_open(src, dst)

    # 공통 서술문 교체
    hwp.find_replace_many(build_narrative_replacements(cfg))

    # 직업재활계획서 고유 교체
    hwp.find_replace_many([
        (f'{ty}년 1월 1일 ~ {ty}년 12월 31일',
         f'{ny}년 1월 1일 ~ {ny}년 12월 31일'),
        (f'{prev_pct}의 수행율을 {curr_pct}로',
         f'{curr_pct}의 수행율을 {next_pct}로'),
        (f'{ty}년 \n\n1월 ~ 9월', f'{ny}년 \n\n1월 ~ 9월'),
    ])

    hwp.save()
    hwp.close()
    return dst


if __name__ == '__main__':
    from core.hwp_engine import HwpEngine
    cfg = load_config()
    hwp = HwpEngine()
    try:
        print(run(cfg, hwp))
    finally:
        hwp.quit()
