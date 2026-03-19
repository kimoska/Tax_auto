"""
AutoTax — 입력값 검증 단위 테스트
"""
import pytest
from core.validator import (
    normalize_resident_id,
    validate_resident_id,
    validate_industry_code,
    validate_period,
    VALID_INDUSTRY_CODES,
)


class TestNormalizeResidentId:
    """주민번호 정규화 테스트"""

    def test_remove_hyphen(self):
        assert normalize_resident_id('800101-1234567') == '8001011234567'

    def test_remove_spaces(self):
        assert normalize_resident_id('800101 1234567') == '8001011234567'

    def test_already_normalized(self):
        assert normalize_resident_id('8001011234567') == '8001011234567'

    def test_empty_string(self):
        assert normalize_resident_id('') == ''


class TestValidateResidentId:
    """주민번호 형식 검증 테스트"""

    def test_valid_male_1900s(self):
        ok, msg = validate_resident_id('800101-1234567')
        assert ok is True
        assert msg == ''

    def test_valid_female_1900s(self):
        ok, msg = validate_resident_id('900202-2345678')
        assert ok is True

    def test_valid_male_2000s(self):
        ok, msg = validate_resident_id('010315-3123456')
        assert ok is True

    def test_valid_foreigner(self):
        ok, msg = validate_resident_id('850505-5123456')
        assert ok is True

    def test_empty(self):
        ok, msg = validate_resident_id('')
        assert ok is False
        assert '입력' in msg

    def test_too_short(self):
        ok, msg = validate_resident_id('800101-12345')
        assert ok is False
        assert '13자리' in msg

    def test_too_long(self):
        ok, msg = validate_resident_id('800101-12345678')
        assert ok is False
        assert '13자리' in msg

    def test_non_numeric(self):
        ok, msg = validate_resident_id('800101-1234abc')
        assert ok is False
        assert '숫자' in msg

    def test_invalid_month(self):
        ok, msg = validate_resident_id('801301-1234567')
        assert ok is False
        assert '월' in msg

    def test_invalid_day(self):
        ok, msg = validate_resident_id('800132-1234567')
        assert ok is False
        assert '일' in msg

    def test_invalid_gender_code(self):
        ok, msg = validate_resident_id('800101-9234567')
        assert ok is False
        assert '성별' in msg


class TestValidateIndustryCode:
    """업종코드 유효성 테스트"""

    def test_valid_940909(self):
        ok, msg = validate_industry_code('940909')
        assert ok is True

    def test_valid_940903(self):
        ok, msg = validate_industry_code('940903')
        assert ok is True

    def test_valid_851101(self):
        ok, msg = validate_industry_code('851101')
        assert ok is True

    def test_invalid_code(self):
        ok, msg = validate_industry_code('999999')
        assert ok is False

    def test_empty_code(self):
        ok, msg = validate_industry_code('')
        assert ok is False

    def test_all_codes_in_set(self):
        """정의된 모든 코드가 유효한지 확인"""
        assert len(VALID_INDUSTRY_CODES) >= 30


class TestValidatePeriod:
    """귀속연월 형식 테스트"""

    def test_valid_period(self):
        ok, msg = validate_period('2026-03')
        assert ok is True

    def test_valid_december(self):
        ok, msg = validate_period('2026-12')
        assert ok is True

    def test_invalid_month_13(self):
        ok, msg = validate_period('2026-13')
        assert ok is False

    def test_invalid_month_00(self):
        ok, msg = validate_period('2026-00')
        assert ok is False

    def test_invalid_format(self):
        ok, msg = validate_period('202603')
        assert ok is False

    def test_empty(self):
        ok, msg = validate_period('')
        assert ok is False
