"""
AutoTax — 세액 계산 엔진
plan.md §9 + prototype.html의 calculateTaxes() 로직 이식

세율 결정 규칙 (plan.md §9.2):
  - 940905 (봉사료수취자): 5%
  - 940904 (직업운동가): 3% (기본, 별도 지정 가능)
  - 그 외 모든 코드: 3%

계산 공식:
  소득세      = floor(지급액 × 세율% / 10) × 10  (원단위 절사)
  지방소득세  = floor(소득세 × 10% / 10) × 10    (원단위 절사)
  실지급액    = 지급액 - 소득세 - 지방소득세
"""
import math


# 업종코드별 세율 매핑 (plan.md §9.2)
TAX_RATE_MAP = {
    '940905': 5,   # 봉사료수취자 → 5%
    # 나머지는 모두 3% (get_tax_rate 함수에서 기본값 처리)
}


def get_tax_rate(industry_code: str) -> int:
    """
    업종코드 → 세율(%) 반환.
    940905 → 5, 그 외 → 3
    """
    return TAX_RATE_MAP.get(industry_code, 3)


def calculate_taxes(total_payment: int, tax_rate_percent: int = 3) -> dict:
    """
    지급액과 세율로 세기 계산.

    Args:
        total_payment: 총 지급액 (원 단위)
        tax_rate_percent: 세율 (3, 5, 20 중 택1)

    Returns:
        dict with keys: income_tax, local_tax, net_payment
    """
    if total_payment <= 0:
        return {
            'income_tax': 0,
            'local_tax': 0,
            'net_payment': 0,
        }

    # 소득세 = floor(지급액 × 세율% / 10) × 10
    rate = tax_rate_percent / 100.0
    income_tax = math.floor(total_payment * rate / 10) * 10

    # 지방소득세 = floor(소득세 × 10% / 10) × 10
    local_tax = math.floor(income_tax * 0.1 / 10) * 10

    # 실지급액
    net_payment = total_payment - income_tax - local_tax

    return {
        'income_tax': income_tax,
        'local_tax': local_tax,
        'net_payment': net_payment,
    }


def calculate_for_instructor(total_payment: int, industry_code: str) -> dict:
    """
    강사의 업종코드 기반으로 세액 계산 (편의 함수).
    Returns: dict with income_tax, local_tax, net_payment, tax_rate
    """
    rate = get_tax_rate(industry_code)
    result = calculate_taxes(total_payment, rate)
    result['tax_rate'] = rate
    result['total_payment'] = total_payment
    result['industry_code'] = industry_code
    return result
