"""HWP COM 자동화 공통 엔진.

한글(HWP) 프로그램의 COM 인터페이스를 래핑하여
파일 열기, 찾아바꾸기, 저장, 텍스트 추출 등 공통 기능을 제공한다.
"""
import win32com.client
import os
import shutil


class HwpEngine:
    """HWP COM 자동화 엔진."""

    def __init__(self, visible=False):
        self._clear_gen_py_cache()
        self.hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
        self.hwp.XHwpWindows.Item(0).Visible = visible
        self.hwp.SetMessageBoxMode(0x00010000)
        try:
            self.hwp.RegisterModule('FilePathCheckDLL', 'FilePathCheckerModule')
        except Exception:
            pass

    def open(self, filepath):
        """HWP 파일 열기."""
        abs_path = os.path.abspath(filepath)
        pset = self.hwp.HParameterSet.HFileOpenSave
        self.hwp.HAction.GetDefault('FileOpen', pset.HSet)
        pset.filename = abs_path
        pset.Format = 'HWP'
        self.hwp.HAction.Execute('FileOpen', pset.HSet)

    def save(self):
        """현재 문서 저장 (덮어쓰기)."""
        self.hwp.HAction.Run('FileSave')

    def close(self):
        """현재 문서 닫기 (저장 안 함)."""
        self.hwp.SetMessageBoxMode(0x00100000)
        self.hwp.Clear(1)
        self.hwp.SetMessageBoxMode(0x00010000)

    def quit(self):
        """HWP 프로그램 종료."""
        try:
            self.hwp.Quit()
        except Exception:
            pass

    def find_replace(self, find_text, replace_text):
        """문서 전체에서 찾아 바꾸기. 교체 횟수 반환."""
        self.hwp.HAction.Run('MoveDocBegin')
        pset = self.hwp.HParameterSet.HFindReplace
        self.hwp.HAction.GetDefault('AllReplace', pset.HSet)
        pset.FindString = find_text
        pset.ReplaceString = replace_text
        pset.FindRegExp = 0
        pset.IgnoreMessage = 1
        result = self.hwp.HAction.Execute('AllReplace', pset.HSet)
        return result

    def find_replace_verified(self, find_text, replace_text, label=''):
        """찾아바꾸기 후 성공 여부 검증. 실패시 축약 매칭 시도."""
        result = self.find_replace(find_text, replace_text)

        # 전체 텍스트에서 원문이 아직 남아있는지 확인
        doc_text = self.get_text()
        if find_text[:30] in doc_text:
            # 축약 매칭 시도: 앞 40자로 재시도
            short_find = find_text[:40]
            if short_find in doc_text:
                print(f'  [재시도] {label}: 축약 매칭 ({short_find[:20]}...)', flush=True)
                self.find_replace(short_find, replace_text)
                doc_text = self.get_text()
                if short_find[:20] not in doc_text and find_text[:20] not in doc_text:
                    return True
            print(f'  [경고] {label}: 교체 실패 — 2024 원문 잔류 가능', flush=True)
            return False
        return True

    def find_replace_many(self, replacements):
        """여러 찾아바꾸기를 순차 실행.

        Args:
            replacements: [(find, replace), ...] 리스트
        """
        for find_text, replace_text in replacements:
            self.find_replace(find_text, replace_text)

    def get_text(self):
        """현재 문서의 전체 텍스트 추출."""
        self.hwp.InitScan(0, 0, 0, 0, 0, 0)
        parts = []
        for _ in range(10000):
            state, text = self.hwp.GetText()
            if state <= 1:
                break
            parts.append(text)
        self.hwp.ReleaseScan()
        return '\n'.join(parts)

    def copy_template_and_open(self, template_path, output_path):
        """템플릿 복사 후 열기.

        Args:
            template_path: 원본 HWP 파일 경로
            output_path: 복사될 출력 경로
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy2(template_path, output_path)
        self.open(output_path)

    @staticmethod
    def _clear_gen_py_cache():
        """gen_py 캐시 삭제 (COM 충돌 방지)."""
        gen_py = os.path.join(
            os.environ.get('LOCALAPPDATA', ''), 'Temp', 'gen_py'
        )
        if os.path.exists(gen_py):
            shutil.rmtree(gen_py, ignore_errors=True)
