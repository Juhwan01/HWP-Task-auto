"""
2025년도 강선미 직업재활 문서 자동 생성기
- 2024 HWP 파일을 템플릿으로 사용 (양식 100% 보존)
- COM FindReplace로 텍스트만 교체
- 서술형 부분은 OpenAI API로 생성 (톤앤매너 유지)
"""
import win32com.client
import os
import json
import sys
import shutil
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, '2025_output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')

with open(os.path.join(BASE_DIR, 'extracted_com.json'), 'r', encoding='utf-8') as f:
    TEXTS = json.load(f)


# ============================================================
# HWP COM 헬퍼 함수
# ============================================================

def create_hwp():
    """HWP COM 객체 생성 (late-binding only, no gen_py)."""
    # gen_py 캐시 강제 삭제
    gen_py_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', 'gen_py')
    if os.path.exists(gen_py_dir):
        shutil.rmtree(gen_py_dir, ignore_errors=True)

    hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
    hwp.XHwpWindows.Item(0).Visible = False

    # 모든 다이얼로그 자동 확인 (핵심!)
    hwp.SetMessageBoxMode(0x00010000)

    try:
        hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
    except:
        pass

    return hwp


def hwp_open(hwp, filepath):
    """HWP 파일 열기."""
    pset = hwp.HParameterSet.HFileOpenSave
    hwp.HAction.GetDefault('FileOpen', pset.HSet)
    pset.filename = filepath
    pset.Format = 'HWP'
    hwp.HAction.Execute('FileOpen', pset.HSet)


def hwp_save(hwp, filepath=None):
    """HWP 파일 저장. filepath 없으면 현재 파일에 덮어쓰기."""
    hwp.HAction.Run('FileSave')


def hwp_close(hwp):
    """현재 문서 닫기 (저장 안함)."""
    hwp.SetMessageBoxMode(0x00100000)  # "저장안함" 자동 선택
    hwp.Clear(1)
    hwp.SetMessageBoxMode(0x00010000)  # 복원


def hwp_find_replace(hwp, find_text, replace_text):
    """찾아 바꾸기 (문서 전체)."""
    hwp.HAction.Run('MoveDocBegin')  # 커서를 문서 시작으로
    pset = hwp.HParameterSet.HFindReplace
    hwp.HAction.GetDefault('AllReplace', pset.HSet)
    pset.FindString = find_text
    pset.ReplaceString = replace_text
    pset.FindRegExp = 0
    pset.IgnoreMessage = 1
    hwp.HAction.Execute('AllReplace', pset.HSet)


def hwp_replace_all(hwp, replacements):
    """여러 찾아바꾸기 실행."""
    for find_text, replace_text in replacements:
        hwp_find_replace(hwp, find_text, replace_text)


def hwp_get_text(hwp):
    """현재 문서의 전체 텍스트 추출."""
    hwp.InitScan()
    texts = []
    for _ in range(10000):
        state, text = hwp.GetText()
        if state <= 1:
            break
        texts.append(text)
    hwp.ReleaseScan()
    return '\n'.join(texts)


# ============================================================
# OpenAI 헬퍼
# ============================================================

SYSTEM_PROMPT = """당신은 장애인 직업재활시설의 직업훈련교사 고경숙입니다.
강선미(지적장애 3급)씨의 직업재활 문서를 작성합니다.

중요한 규칙:
1. 톤앤매너: 제공된 2024년 원본 문서의 문체, 어미, 호칭, 표현 패턴을 완전히 동일하게 유지하세요.
2. "~함", "~보임", "~있음" 등의 어미가 원본에서 쓰였으면 그대로, "~하였습니다" 등 존대가 쓰였으면 그대로 따르세요.
3. 숫자/점수 표기 방식(예: "100점중 93점", "3점에서 4점으로")도 원본과 동일하게 유지하세요.
4. 구조와 항목 순서는 원본과 완전히 동일하게 유지하세요.
5. 달라지는 것은 오직 연도, 점수, 날짜 등 팩트(사실)만입니다.
6. 절대 새로운 표현이나 내용을 창작하지 마세요. 원본의 패턴을 따라가세요."""


def ask_openai(user_prompt):
    """OpenAI API 호출."""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content


# ============================================================
# 문서별 생성 로직
# ============================================================

def gen_01(hwp):
    """1. 직업평가계획서 - 단순 날짜 변경."""
    src = os.path.join(BASE_DIR, '1.2024년 강선미 직업평가계획서.hwp')
    dst = os.path.join(OUTPUT_DIR, '1.2025년 강선미 직업평가계획서.hwp')
    shutil.copy2(src, dst)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2024. 10. 04.', '2025. 10. 04.'),
        ('2024. 10. 02.', '2025. 10. 02.'),
        ('2024.  10.  02.', '2025.  10.  02.'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)
    print('[1/6] 직업평가계획서 완료', flush=True)


def gen_02(hwp):
    """2. 상담기록지 - 날짜 변경 + OpenAI로 상담내용 생성."""
    src = os.path.join(BASE_DIR, '2024년도 강선미 상담기록지.hwp')
    dst = os.path.join(OUTPUT_DIR, '2025년도 강선미 상담기록지.hwp')
    shutil.copy2(src, dst)

    ref_text = TEXTS['2024년도 강선미 상담기록지.hwp']

    prompt = f"""아래는 2024년도 강선미씨의 상담기록지 원본입니다. 3회 상담 기록이 있습니다.

--- 2024년 원본 ---
{ref_text}
--- 원본 끝 ---

2025년도 상담기록지의 각 회차 상담내용을 작성해주세요.

기본 정보:
- 상담자: 고경숙(인/서명), 상담장소: 상담실, 관계: 본인
- 1회차: 2025년 2월 17일 (13:40-14:00), 목적: ⑥고충상담
- 2회차: 2025년 5월 22일 (10:10-10:30), 목적: ⑥고충상담
- 3회차: 2025년 8월 12일 (14:20-14:40), 목적: ⑤사례관리

2025년 상황:
- 2024년 현장평가: 전체 93% → 2025년: 전체 94% (소폭 개선)
- 의사소통/대인관계: 89% → 91%로 개선됨
- 체중관리 프로그램 참여 시작 (2024년 8월 상담에서 권유했었음)
- 동료들과의 관계가 조금씩 나아지고 있음
- 여전히 내성적이지만 이전보다 표현이 나아짐

각 회차별로 아래 형식으로 작성:
[1회차]
상담내용: (원본과 동일한 톤으로)
상담결과 및 지원계획: (원본과 동일한 톤으로)
슈퍼비전: (원본과 동일한 톤으로)

[2회차]
...

[3회차]
..."""

    result = ask_openai(prompt)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2024년 2월 19일', '2025년 2월 17일'),
        ('2024년 5월 23일', '2025년 5월 22일'),
        ('2024년  8월  13일', '2025년  8월  12일'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)

    with open(os.path.join(OUTPUT_DIR, '_02_상담기록지_생성내용.txt'), 'w', encoding='utf-8') as f:
        f.write(result)

    print('[2/6] 상담기록지 완료', flush=True)
    return result


def gen_03(hwp):
    """3. 직업재활계획수립상담."""
    src = os.path.join(BASE_DIR, '3.2024년 강선미 직업재활계획수립상담.hwp')
    dst = os.path.join(OUTPUT_DIR, '3.2025년 강선미 직업재활계획수립상담.hwp')
    shutil.copy2(src, dst)

    ref_text = TEXTS['3.2024년 강선미 직업재활계획수립상담.hwp']

    prompt = f"""아래는 2024년도 강선미씨의 직업재활계획수립상담 기록 원본입니다.

--- 2024년 원본 ---
{ref_text}
--- 원본 끝 ---

2025년도 버전의 상담내용, 상담결과 및 지원계획, 슈퍼비전을 작성해주세요.

변경 데이터:
- 상담일시: 2025년 10월 15일 (13:00 - 13:20)
- 현장평가: 2025년 10월 4일 실시
- 2025년 현장평가 결과: 작업태도 101/110(92%), 의사소통/대인관계 82/90(91%), 전체 94%
- 전년도(2024년) 대비: 작업태도 91%→92%(1%↑), 의사소통 89%→91%(2%↑)
- "전년도"는 2024년, "차기년도"는 2026년
- 단기목표: 전년도에 이어 동일 재설정 (소폭 개선은 되었으나 지속 필요)

각 섹션별로 작성:
[상담내용]
(본문)

[상담결과 및 지원계획]
(본문)

[슈퍼비전]
(본문)"""

    result = ask_openai(prompt)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2024년  10월 15일', '2025년  10월 15일'),
        ('2024년 10월 15일', '2025년 10월 15일'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)

    with open(os.path.join(OUTPUT_DIR, '_03_직업재활계획수립상담_생성내용.txt'), 'w', encoding='utf-8') as f:
        f.write(result)

    print('[3/6] 직업재활계획수립상담 완료', flush=True)
    return result


def gen_04(hwp):
    """4. 직업평가보고서."""
    src = os.path.join(BASE_DIR, '4.2024년 강선미 직업평가보고서.hwp')
    dst = os.path.join(OUTPUT_DIR, '4.2025년 강선미 직업평가보고서.hwp')
    shutil.copy2(src, dst)

    ref_text = TEXTS['4.2024년 강선미 직업평가보고서.hwp']

    prompt = f"""아래는 2024년도 강선미씨의 직업평가보고서 원본입니다.

--- 2024년 원본 ---
{ref_text}
--- 원본 끝 ---

2025년도 버전의 서술형 부분을 작성해주세요.

변경 데이터:
- 평가일: 2025년 10월 04일
- 2025년 결과: 작업규칙 50/50(100%), 작업태도 101/110(92%), 의사소통/대인관계 82/90(91%), 직무기술 40/40(100%), 전체 273/290(94%)
- 진전도: 2024년→2025년 비교 (작업규칙 100%→100%, 작업태도 91%→92% 1%↑, 의사소통 89%→91% 2%↑, 직무기술 100%→100%, 전체 93%→94% 1%↑)
- 단기목표: "어려운 일에 처했을 때 관리자와 동료에게 도움을 구한다", "본인의 의사를 분명하고 적절하게 표현한다" - 전년도에 이어 지속

다음 섹션을 작성:
[현장평가 결과 서술] (점수표 아래 서술 부분)

[진전도 평가결과 서술]

[종합소견 및 직업재활방향]
1. 직업적 강점/약점
2. 직업적 목표 (직업목표, 장기목표, 단기목표)
3. 종합소견

날짜: 2025년 10월 18일"""

    result = ask_openai(prompt)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2024년 10월 04일', '2025년 10월 04일'),
        # 점수 교체
        ('\n100\n', '\n101\n'),
        ('\n80\n', '\n82\n'),
        ('91%', '92%'),
        ('89%', '91%'),
        ('270', '273'),
        ('93%', '94%'),
        # 진전도 연도
        ('2023년 수행율', '2024년 수행율'),
        # 날짜
        ('2024년  10월  18일', '2025년  10월  18일'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)

    with open(os.path.join(OUTPUT_DIR, '_04_직업평가보고서_생성내용.txt'), 'w', encoding='utf-8') as f:
        f.write(result)

    print('[4/6] 직업평가보고서 완료', flush=True)
    return result


def gen_05(hwp):
    """5. 사례회의록."""
    src = os.path.join(BASE_DIR, '5.2024년 강선미 직업재활수립 사례회의록.hwp')
    dst = os.path.join(OUTPUT_DIR, '5.2025년 강선미 직업재활수립 사례회의록.hwp')
    shutil.copy2(src, dst)

    ref_text = TEXTS['5.2024년 강선미 직업재활수립 사례회의록.hwp']

    prompt = f"""아래는 2024년도 강선미씨의 직업재활수립 사례회의록 원본입니다.

--- 2024년 원본 ---
{ref_text}
--- 원본 끝 ---

2025년도 버전의 회의내용과 회의결과를 작성해주세요.

변경 데이터:
- 일시: 2025년 10월 28일
- 현장평가 실시일: 2025년 10월 4일
- 2025년 결과: 작업규칙 50/50(100%), 작업태도 101/110(92%), 의사소통/대인관계 82/90(91%), 직무기술 40/40(100%), 전체 273/290(94%)
- 진전도: 2024년 93%→2025년 94% (1% 상승), 작업태도 1%↑, 의사소통 2%↑
- 장기목표: 의사소통/대인관계 향상 (전년도에 이어 지속)
- 단기목표: 어려운 일에 도움 구하기 + 의사 분명하게 표현하기

다음 형식으로 작성:
[회의내용1] (현장평가 결과 보고 부분)

[회의내용2] (진전도 평가 부분)

[회의내용3] (관리부장, 사무국장 의견)

[회의결과]

원본의 대화체 형식("-사무국장 김남근:", "-직업훈련교사 고경숙:" 등)을 완전히 유지하세요."""

    result = ask_openai(prompt)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2024년 10월 28일', '2025년 10월 28일'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)

    with open(os.path.join(OUTPUT_DIR, '_05_사례회의록_생성내용.txt'), 'w', encoding='utf-8') as f:
        f.write(result)

    print('[5/6] 사례회의록 완료', flush=True)
    return result


def gen_06(hwp):
    """6. 직업재활계획서 - 날짜/점수 교체."""
    src = os.path.join(BASE_DIR, '6.2024년 강선미 직업재활계획서.hwp')
    dst = os.path.join(OUTPUT_DIR, '6.2025년 강선미 직업재활계획서.hwp')
    shutil.copy2(src, dst)

    hwp_open(hwp, dst)
    hwp_replace_all(hwp, [
        ('2025년 1월 1일 ~ 2025년 12월 31일', '2026년 1월 1일 ~ 2026년 12월 31일'),
        ('2024년 10월 15일', '2025년 10월 15일'),
        ('2024년 10월 04일', '2025년 10월 04일'),
        ('89%의 수행율을 91%로', '91%의 수행율을 93%로'),
        ('2025년', '2026년'),
        ('2024년\n\n10월 28일', '2025년\n\n10월 28일'),
        ('2024.  10.  31.', '2025.  10.  31.'),
    ])
    hwp_save(hwp, dst)
    hwp_close(hwp)
    print('[6/6] 직업재활계획서 완료', flush=True)


# ============================================================
# 메인
# ============================================================

def main():
    print('=== 2025년도 문서 생성 시작 ===', flush=True)
    print(f'모델: {MODEL}', flush=True)

    hwp = create_hwp()
    print('HWP COM 초기화 완료', flush=True)

    try:
        gen_01(hwp)
        gen_02(hwp)
        gen_03(hwp)
        gen_04(hwp)
        gen_05(hwp)
        gen_06(hwp)

        print('\n=== 모든 문서 생성 완료! ===', flush=True)
        print(f'출력 폴더: {OUTPUT_DIR}', flush=True)
        print('\n[중요] 서술형 부분이 _*.txt 파일로 생성되었습니다.', flush=True)
        print('각 HWP 파일을 열어 해당 서술 부분을 txt 내용으로 교체하세요.', flush=True)

    except Exception as e:
        print(f'\n에러: {e}', flush=True)
        import traceback
        traceback.print_exc()
    finally:
        try:
            hwp.Quit()
        except:
            pass


if __name__ == '__main__':
    main()
