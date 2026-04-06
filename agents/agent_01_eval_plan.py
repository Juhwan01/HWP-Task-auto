"""에이전트 01: 직업평가계획서 (FindReplace only)."""
from agents.base import load_config, template_path, output_path, build_narrative_replacements, enrich_cfg_from_eval


def run(cfg, hwp, ai=None):
    src = template_path(cfg, '01_eval_plan')
    dst = output_path(cfg, '01_eval_plan')

    cfg = enrich_cfg_from_eval(cfg)
    hwp.copy_template_and_open(src, dst)
    hwp.find_replace_many(build_narrative_replacements(cfg))
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
