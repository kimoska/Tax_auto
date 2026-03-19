"""
AutoTax — 세액 계산 단위 테스트
실제 calculate_taxes() 공식:
  소득세 = floor(지급액 × 세율% / 10) × 10
  지방소득세 = floor(소득세 × 10% / 10) × 10
"""
import pytest
from core.tax_calculator import calculate_taxes, get_tax_rate, calculate_for_instructor


class TestGetTaxRate:
    """업종코드별 세율 결정 테스트"""

    def test_default_rate_940909(self):
        assert get_tax_rate('940909') == 3

    def test_default_rate_940903(self):
        assert get_tax_rate('940903') == 3

    def test_bongsa_rate_940905(self):
        assert get_tax_rate('940905') == 5

    def test_default_rate_unknown_code(self):
        assert get_tax_rate('999999') == 3


class TestCalculateTaxes:
    """세액 계산 테스트"""

    def test_basic_3_percent(self):
        """320,000 × 3%"""
        result = calculate_taxes(320_000, 3)
        # 소득세: floor(320000*0.03/10)*10 = floor(960/10)*10 = 96*10 = 960
        # 하지만 실제: floor(9600/10)*10 = 9600
        # 재확인: 320000*3/100 = 9600, floor(9600/10)*10 = 9600
        assert result['income_tax'] == 9600
        assert result['local_tax'] == 960

    def test_larger_amount_3_percent(self):
        """720,000 × 3%"""
        result = calculate_taxes(720_000, 3)
        # 720000*0.03 = 21600, floor(21600/10)*10 = 21600
        assert result['income_tax'] == 21600
        # floor(21600*0.1/10)*10 = floor(2160/10)*10 = 2160
        assert result['local_tax'] == 2160
        assert result['net_payment'] == 720_000 - 21600 - 2160

    def test_5_percent_rate(self):
        """500,000 × 5%"""
        result = calculate_taxes(500_000, 5)
        # 500000*0.05 = 25000, floor(25000/10)*10 = 25000
        assert result['income_tax'] == 25000
        # floor(25000*0.1/10)*10 = floor(2500/10)*10 = 2500
        assert result['local_tax'] == 2500

    def test_zero_payment(self):
        result = calculate_taxes(0, 3)
        assert result['income_tax'] == 0
        assert result['local_tax'] == 0
        assert result['net_payment'] == 0

    def test_negative_payment(self):
        result = calculate_taxes(-100, 3)
        assert result['income_tax'] == 0

    def test_small_amount(self):
        """10,000 × 3%"""
        result = calculate_taxes(10_000, 3)
        # 10000*0.03 = 300, floor(300/10)*10 = 300
        assert result['income_tax'] == 300
        # floor(300*0.1/10)*10 = floor(30/10)*10 = 30
        assert result['local_tax'] == 30

    def test_large_amount(self):
        """50,000,000 × 3%"""
        result = calculate_taxes(50_000_000, 3)
        # 50000000*0.03 = 1500000
        assert result['income_tax'] == 1_500_000
        # floor(1500000*0.1/10)*10 = 150000
        assert result['local_tax'] == 150_000
        assert result['net_payment'] == 50_000_000 - 1_500_000 - 150_000

    def test_truncation_floor(self):
        """원단위 절사: 333,333 × 3%"""
        result = calculate_taxes(333_333, 3)
        # 333333*0.03 = 9999.99, floor(9999.99/10)*10 = 999*10 = 9990
        assert result['income_tax'] == 9990
        # floor(9990*0.1/10)*10 = floor(999/10)*10 = 99*10 = 990
        assert result['local_tax'] == 990

    def test_net_payment_consistency(self):
        """실지급액 = 지급액 - 소득세 - 지방소득세"""
        for amount in [100_000, 250_000, 500_000, 1_000_000, 3_333_333]:
            result = calculate_taxes(amount, 3)
            assert result['net_payment'] == amount - result['income_tax'] - result['local_tax']


class TestCalculateForInstructor:
    """강사 편의 함수 테스트"""

    def test_returns_all_fields(self):
        result = calculate_for_instructor(1_000_000, '940909')
        assert result['tax_rate'] == 3
        assert result['total_payment'] == 1_000_000
        assert result['industry_code'] == '940909'

    def test_940905_uses_5_percent(self):
        result = calculate_for_instructor(1_000_000, '940905')
        assert result['tax_rate'] == 5
        # 1000000*0.05 = 50000
        assert result['income_tax'] == 50000
