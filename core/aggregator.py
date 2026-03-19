"""
AutoTax — 동일 강사 합산 로직 (정산용)
plan.md §4.1 파이프라인: lectures → settlements 변환
"""
from core.tax_calculator import calculate_for_instructor


def aggregate_lectures_to_settlements(lectures: list[dict]) -> list[dict]:
    """
    월별 강의 내역을 강사별로 합산하여 정산 데이터 생성.

    Args:
        lectures: repository.get_lectures_by_period() 결과
                  (instructor_id, instructor_name, industry_code,
                   is_foreigner, resident_id, payment_amount, ... 포함)

    Returns:
        list[dict] — 강사별 합산 정산 데이터
        각 dict: instructor_id, name, resident_id, industry_code, is_foreigner,
                 total_payment, tax_rate, income_tax, local_tax, net_payment,
                 categories(set), program_names(list)
    """
    aggregated = {}

    for lec in lectures:
        iid = lec['instructor_id']

        if iid not in aggregated:
            aggregated[iid] = {
                'instructor_id': iid,
                'name': lec.get('instructor_name', ''),
                'resident_id': lec.get('resident_id', ''),
                'industry_code': lec.get('industry_code', '940909'),
                'is_foreigner': lec.get('is_foreigner', '1'),
                'total_payment': 0,
                'categories': set(),
                'program_names': [],
            }

        entry = aggregated[iid]
        entry['total_payment'] += lec.get('payment_amount', 0)

        # 과목구분 수집
        cat = lec.get('program_category', '')
        if cat:
            entry['categories'].add(cat)

        # 프로그램명 수집
        pname = lec.get('program_name', '')
        if pname and pname not in entry['program_names']:
            entry['program_names'].append(pname)

    # 세액 계산
    results = []
    for iid, entry in aggregated.items():
        tax_data = calculate_for_instructor(
            entry['total_payment'],
            entry['industry_code']
        )
        entry.update({
            'tax_rate': tax_data['tax_rate'],
            'income_tax': tax_data['income_tax'],
            'local_tax': tax_data['local_tax'],
            'net_payment': tax_data['net_payment'],
        })
        # set → list 변환 (직렬화 대비)
        entry['categories'] = list(entry['categories'])
        results.append(entry)

    # 이름 순 정렬
    results.sort(key=lambda x: x['name'])
    return results
