"""eval_parser 단위 테스트.

실제 현장평가 텍스트 파일을 파싱하여 영역별 점수, 수행율, 요약 등을 검증한다.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.eval_parser import (
    parse_eval_text, load_eval_parsed, format_for_prompt, compare_years,
)


# ── 2025 파싱 테스트 ──

class Test2025Parsing:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed = load_eval_parsed(2025)
        if self.parsed is None:
            pytest.skip('2025 현장평가 텍스트 파일 없음')

    def test_basic_info(self):
        info = self.parsed['basic_info']
        assert info['name'] is not None
        assert '2025' in info['eval_date']
        assert info['disability'] is not None
        assert info['case_manager'] is not None

    def test_sections_exist(self):
        sections = self.parsed['sections']
        for name in ['작업규칙', '작업태도', '의사소통', '직무기술']:
            assert name in sections, f'{name} 영역 누락'

    def test_section_scores_2025(self):
        expected = {
            '작업규칙': (50, 50, 100.0),
            '작업태도': (101, 110, 91.8),
            '의사소통': (82, 90, 91.1),
            '직무기술': (40, 40, 100.0),
        }
        for name, (score, total, pct) in expected.items():
            sec = self.parsed['sections'][name]
            assert sec['score'] == score, f'{name} score: {sec["score"]} != {score}'
            assert sec['total'] == total, f'{name} total: {sec["total"]} != {total}'
            assert sec['pct'] == pct, f'{name} pct: {sec["pct"]} != {pct}'

    def test_summary_2025(self):
        s = self.parsed['summary']
        assert s['total_score'] == 273
        assert s['total_possible'] == 290
        assert s['total_pct'] == 94.0

    def test_items_count_2025(self):
        expected_counts = {
            '작업규칙': 10,
            '작업태도': 22,
            '의사소통': 18,
            '직무기술': 8,
        }
        for name, count in expected_counts.items():
            items = self.parsed['sections'][name]['items']
            assert len(items) == count, f'{name} items: {len(items)} != {count}'

    def test_item_scores_valid(self):
        for name, sec in self.parsed['sections'].items():
            for item in sec['items']:
                assert 1 <= item['score'] <= 5, f'{name}: 점수 범위 초과 {item}'
                assert len(item['text']) >= 5, f'{name}: 항목 텍스트 너무 짧음 {item}'

    def test_items_sum_matches_total(self):
        for name, sec in self.parsed['sections'].items():
            if sec['items']:
                items_sum = sum(it['score'] for it in sec['items'])
                assert items_sum == sec['score'], \
                    f'{name}: 항목합 {items_sum} != 총점 {sec["score"]}'


# ── 2024 파싱 테스트 ──

class Test2024Parsing:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed = load_eval_parsed(2024)
        if self.parsed is None:
            pytest.skip('2024 현장평가 텍스트 파일 없음')

    def test_section_scores_2024(self):
        expected = {
            '작업규칙': (50, 50, 100.0),
            '작업태도': (100, 110, 90.9),
            '의사소통': (80, 90, 88.9),
            '직무기술': (40, 40, 100.0),
        }
        for name, (score, total, pct) in expected.items():
            sec = self.parsed['sections'][name]
            assert sec['score'] == score, f'{name} score: {sec["score"]} != {score}'
            assert sec['total'] == total, f'{name} total: {sec["total"]} != {total}'
            assert sec['pct'] == pct, f'{name} pct: {sec["pct"]} != {pct}'

    def test_summary_2024(self):
        s = self.parsed['summary']
        assert s['total_score'] == 270
        assert s['total_possible'] == 290
        assert s['total_pct'] == 93.0


# ── 연도 비교 테스트 ──

class TestCompareYears:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.p2024 = load_eval_parsed(2024)
        self.p2025 = load_eval_parsed(2025)
        if not self.p2024 or not self.p2025:
            pytest.skip('2024/2025 현장평가 텍스트 파일 없음')

    def test_compare_output_not_empty(self):
        result = compare_years(self.p2024, self.p2025)
        assert len(result) > 0

    def test_compare_contains_total_change(self):
        result = compare_years(self.p2024, self.p2025)
        assert '270' in result and '273' in result
        assert '93.0%' in result and '94.0%' in result

    def test_compare_direction(self):
        result = compare_years(self.p2024, self.p2025)
        assert '상승' in result


# ── format_for_prompt 테스트 ──

class TestFormatForPrompt:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.parsed = load_eval_parsed(2025)
        if self.parsed is None:
            pytest.skip('2025 현장평가 텍스트 파일 없음')

    def test_format_contains_sections(self):
        text = format_for_prompt(self.parsed)
        for name in ['작업규칙', '작업태도', '의사소통', '직무기술']:
            assert name in text

    def test_format_contains_summary(self):
        text = format_for_prompt(self.parsed)
        assert '273/290' in text
        assert '94.0%' in text


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
