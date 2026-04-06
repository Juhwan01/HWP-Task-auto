"""연도 전환 스크립트.

매년 작업 완료 후 실행하여 config.json을 다음 연도용으로 준비한다.
- base_year / target_year를 +1
- curr_year 점수를 prev_year로 이동
- curr_year 점수를 0으로 초기화
- 이번 output 파일들을 다음 연도 templates로 복사
"""
import json
import os
import shutil
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print(f'  config.json 저장 완료')


def advance(dry_run=False):
    cfg = load_config()
    old_by = cfg['base_year']
    old_ty = cfg['target_year']
    new_by = old_by + 1
    new_ty = old_ty + 1

    print(f'=== 연도 전환: {old_ty} → {new_ty} ===')
    print(f'  base_year: {old_by} → {new_by}')
    print(f'  target_year: {old_ty} → {new_ty}')

    # 1. 점수 이동: curr_year → prev_year, curr_year 초기화
    curr_scores = cfg['scores']['curr_year']
    print(f'  prev_year 점수 ← curr_year: {curr_scores}')

    zero_scores = {k: [0, v[1]] for k, v in curr_scores.items()}
    print(f'  curr_year 점수 → 초기화: {zero_scores}')

    # 2. output → templates 복사
    template_dir = os.path.join(BASE_DIR, 'templates')
    output_dir = os.path.join(BASE_DIR, 'output')
    copied = []
    for key, pattern in cfg['outputs'].items():
        src_name = pattern.format(base_year=old_by, target_year=old_ty, name=cfg['name'])
        src_path = os.path.join(output_dir, src_name)
        # 새 템플릿 이름: target_year가 새 base_year가 됨
        tpl_pattern = cfg['templates'][key]
        dst_name = tpl_pattern.format(base_year=new_by, target_year=new_ty, name=cfg['name'])
        dst_path = os.path.join(template_dir, dst_name)

        if os.path.exists(src_path):
            print(f'  복사: output/{src_name} → templates/{dst_name}')
            copied.append((src_path, dst_path))
        else:
            print(f'  [스킵] output/{src_name} 없음')

    if dry_run:
        print('\n  --dry-run: 실제 변경 없음')
        return

    # 실행
    cfg['base_year'] = new_by
    cfg['target_year'] = new_ty
    cfg['scores']['prev_year'] = curr_scores
    cfg['scores']['curr_year'] = zero_scores
    save_config(cfg)

    for src_path, dst_path in copied:
        shutil.copy2(src_path, dst_path)

    print(f'\n완료. 다음 단계:')
    print(f'  1. 현장평가 파일을 evals/{new_ty}/ 에 배치')
    print(f'  2. python run_all.py 실행')


if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    advance(dry_run=dry_run)
