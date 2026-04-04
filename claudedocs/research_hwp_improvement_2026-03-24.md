# HWP 문서 자동화 개선 방향 리서치

> 날짜: 2026-03-24
> 상태: 완료

## 1. 현재 문제점

### 핵심 문제: 2024년 내용이 HWP에 잔류함

| 에이전트 | 문제 | 심각도 |
|---------|------|--------|
| agent_02 (상담기록지) | AI 생성 결과가 HWP에 전혀 삽입되지 않음. txt만 저장. 2024 상담내용 그대로 남음 | CRITICAL |
| agent_03 (수립상담) | `find_replace(old_text, new_text)` 방식 — AI 블록 파싱 실패시 2024 원문 잔존 | HIGH |
| agent_04 (보고서) | 동일 | HIGH |
| agent_05 (회의록) | 동일 | HIGH |

### 근본 원인

1. **find_replace 한계**: 긴 서술문을 통째로 find_replace하는 방식은 HWP 내부 서식/줄바꿈 차이로 매칭 실패 가능
2. **블록 파싱 불안정**: AI가 `[블록:key]` 형식을 정확히 따르지 않으면 전체 교체 실패
3. **agent_02 미구현**: AI 결과 → HWP 삽입 코드 자체가 없음
4. **검증 없음**: 교체 성공 여부를 확인하는 로직 없음

---

## 2. 발견한 해결 도구들

### A. pyhwpx (이미 설치됨! v1.7.2)

`put_field_text()` 메서드가 핵심.

**방식**: HWP 템플릿에 **누름틀(필드)** 을 미리 배치 → Python에서 dict로 한번에 채움

```python
from pyhwpx import Hwp

hwp = Hwp()
hwp.open("template.hwp")
hwp.put_field_text({
    "상담내용_1회": "생성된 1회차 상담 내용...",
    "상담결과_1회": "생성된 1회차 결과...",
    "eval_narrative": "현장평가 결과 서술...",
})
hwp.save_as("output.hwp")
```

**장점**:
- find_replace와 달리 **정확한 위치**에 삽입 (매칭 실패 없음)
- dict 기반이라 코드가 깔끔
- 이미 설치되어 있음

**필요 작업**:
- 6개 HWP 템플릿에 누름틀 필드를 수동으로 배치해야 함 (1회성)
- 템플릿을 `templates_v2/`로 별도 관리

### B. HWP MCP Server (crowwan/hwp-mcp-advanced-custom)

- 59개 한글 제어 함수 제공
- `insert_text_at_position` — 정밀 위치 지정 삽입
- `find_and_replace`, `get_text_all` 등

**장점**: Claude가 MCP를 통해 직접 HWP를 조작 가능
**단점**: 현재 프로젝트는 Python 스크립트 기반이므로 MCP 도입은 아키텍처 변경 필요

### C. hwp.SetTextFile() / hwp.insert_file()

- 현재 사용 중인 win32com 위에서 대용량 텍스트 삽입 가능
- `hwp.MoveToField("필드명")` → `hwp.SetTextFile(...)` 조합

---

## 3. 추천 방향 (3가지 선택지)

### 선택지 1: pyhwpx put_field_text 방식 (추천)

> 난이도: 중 | 안정성: 높 | 변경 범위: 템플릿 + 에이전트 코드

**작업**:
1. 6개 HWP 템플릿에 누름틀 필드 배치 (수동, 1회)
2. `hwp_engine.py`에 pyhwpx 기반 `fill_fields()` 메서드 추가
3. 각 에이전트를 `put_field_text` 방식으로 전환
4. 교체 검증 로직 추가

**결과**: find_replace 매칭 실패 문제 완전 해결

### 선택지 2: 현재 구조 보강 (최소 변경)

> 난이도: 하 | 안정성: 중 | 변경 범위: 에이전트 코드만

**작업**:
1. agent_02에 AI 결과 → HWP 삽입 코드 추가
2. 블록 파싱 실패시 fallback 로직 추가
3. find_replace 후 검증 (교체 전후 텍스트 비교)
4. 실패시 재시도 또는 경고

**한계**: find_replace 근본 문제는 남음

### 선택지 3: HWP MCP 서버 도입

> 난이도: 상 | 안정성: ? | 변경 범위: 전체 아키텍처

**작업**:
1. crowwan/hwp-mcp-advanced-custom 설치
2. Claude Desktop 또는 Claude Code에서 MCP 서버 연결
3. AI가 직접 HWP 문서를 조작하는 워크플로우

**장점**: Claude가 문서를 직접 보고 수정 가능
**리스크**: 안정성 미검증, 아키텍처 대폭 변경

---

## 4. 결론

**선택지 1 (pyhwpx put_field_text) 추천.**

이유:
- pyhwpx가 이미 설치되어 있음
- 누름틀 방식은 한글 문서 자동화의 표준 패턴
- find_replace의 근본 문제를 해결
- 기존 코드 구조(agents + core)와 호환

즉시 가능한 빠른 수정:
- agent_02의 AI 결과 → HWP 삽입 누락 수정 (선택지 2의 일부)
- 블록 파싱 fallback 추가

---

## Sources

- [pyhwpx PyPI](https://pypi.org/project/pyhwpx/)
- [pyhwpx GitHub](https://github.com/martiniifun/pyhwpx)
- [pyhwpx put_field_text 6가지 자료구조](https://pyhwpx.com/519)
- [pyhwpx Cookbook: 텍스트 입력](https://wikidocs.net/257896)
- [Advanced HWP MCP Server (crowwan)](https://glama.ai/mcp/servers/@crowwan/hwp-mcp-advanced-custom)
- [HWP MCP (jkf87)](https://github.com/jkf87/hwp-mcp)
- [한컴디벨로퍼 포럼](https://forum.developer.hancom.com/c/hwp-automation/52)
