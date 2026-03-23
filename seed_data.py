"""
홈택스 이미지 데이터로 DB 초기화 스크립트
18명 강사 + 프로그램 + 강의 + 정산 데이터 입력
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.connection import DatabaseConnection
from db.repository import Repository
from core.aggregator import aggregate_lectures_to_settlements

def main():
    repo = Repository()
    db = repo.db

    # ── 기존 데이터 삭제 ──
    print("기존 데이터 삭제 중...")
    db.execute("DELETE FROM settlements")
    db.execute("DELETE FROM lectures")
    db.execute("DELETE FROM instructor_programs")
    db.execute("DELETE FROM instructors")
    db.execute("DELETE FROM audit_logs")
    print("✔ 기존 데이터 삭제 완료")

    # ── 18명 강사 데이터 (이미지 기준) ──
    # (번호, 카테고리, 프로그램명, 업종구분(업종코드), 강사명, 주민등록번호, 회당강사비)
    instructors_data = [
        ("사회교육프로그램", "영어",                   "940909", "전이부",  "721015-2545624", 50000),
        ("사회교육프로그램", "중국어",                  "940909", "함숙자",  "750129-2053015", 50000),
        ("사회교육프로그램", "일본어",                  "940909", "김건영",  "610126-2017237", 50000),
        ("사회교육프로그램", "라인/웨스턴댄스",          "940902", "최강호",  "560316-2068518", 50000),
        ("사회교육프로그램", "클래식기타",              "940902", "신경숙",  "600815-2009743", 70000),
        ("사회교육프로그램", "가요교실",                "940902", "주혜민",  "710626-2001818", 50000),
        ("사회교육프로그램", "우리춤체조",              "940902", "김경옥",  "600824-2036112", 50000),
        ("사회교육프로그램", "태극권",                  "940909", "안용언",  "620201-1063211", 50000),
        ("사회교육프로그램", "감성수채화/에테가미",      "940909", "성영심",  "630801-2019718", 50000),
        ("사회교육프로그램", "힐링요가/실버필라테스",    "940909", "박선영",  "781231-2541310", 40000),
        ("사회교육프로그램", "가곡",                    "940902", "김현주",  "701122-2000113", 50000),
        ("사회교육프로그램", "우쿨렐레",                "940902", "이현주",  "730905-2025026", 40000),
        ("사회교육프로그램", "문화로배우는일본어",      "940909", "노연희",  "671113-2670818", 50000),
        ("사회교육프로그램", "첫걸음방송댄스",          "940902", "김호준",  "990211-1074515", 50000),
        ("사회교육프로그램", "코어체조",                "940902", "박상미",  "720805-2621623", 50000),
        ("사회교육프로그램", "손가락난타",              "940902", "윤지원",  "740710-2006111", 40000),
        ("사회교육프로그램", "라틴댄스",                "940909", "배정호",  "760103-1036314", 50000),
        ("사회교육프로그램", "아트캘리",                "940909", "장용아",  "901207-2056514", 50000),
    ]

    period = "2026-02"
    year, month = period.split("-")

    for idx, (category, program_name, industry_code, name, resident_id, fee) in enumerate(instructors_data, 1):
        # is_foreigner: '1' = 내국인
        instructor_id = repo.create_instructor({
            'name': name,
            'resident_id': resident_id,
            'industry_code': industry_code,
            'is_foreigner': '1',
        })
        print(f"  [{idx:2d}] 강사 등록: {name} ({resident_id}) → ID={instructor_id}")

        # 프로그램 등록
        program_id = repo.create_program({
            'instructor_id': instructor_id,
            'category': category,
            'program_name': program_name,
            'fee_per_session': fee,
        })

        # 강의 등록 (이번달, 세션 수는 지급액/회당강사비로 역산할 수 있지만
        # 홈택스 이미지에서는 총 지급액만 보이므로, 기본 1회로 설정)
        # 실제 지급액은 이미지 2번에서 볼 수 있는 값을 사용
        repo.create_lecture({
            'instructor_id': instructor_id,
            'program_id': program_id,
            'period': period,
            'payment_month': period,
            'session_count': 4,
            'fee_per_session': fee,
        })

    print(f"\n✔ {len(instructors_data)}명 강사 + 프로그램 + 강의 등록 완료")

    # ── 정산 재계산 ──
    print("\n정산 재계산 중...")
    lectures = repo.get_lectures_by_period(period)
    aggregated = aggregate_lectures_to_settlements(lectures)

    for entry in aggregated:
        calc_data = {
            'total_payment': entry['total_payment'],
            'industry_code': entry['industry_code'],
            'is_foreigner': entry['is_foreigner'],
            'tax_rate': entry['tax_rate'],
            'income_tax': entry['income_tax'],
            'local_tax': entry['local_tax'],
            'net_payment': entry['net_payment'],
        }
        repo.upsert_settlement(entry['instructor_id'], period, calc_data)

    print(f"✔ {len(aggregated)}명 정산 완료")

    # ── 결과 확인 ──
    settlements = repo.get_settlements_by_period(period)
    print(f"\n=== 정산 결과 ({period}) ===")
    print(f"{'번호':>4} {'성명':<6} {'주민번호':<16} {'업종코드':<8} {'지급액':>10} {'소득세':>8} {'지방세':>8}")
    print("-" * 70)
    for i, s in enumerate(settlements, 1):
        print(f"{i:4d} {s['name']:<6} {s['resident_id']:<16} {s['industry_code']:<8} {s['total_payment']:>10,} {s['final_income_tax']:>8,} {s['final_local_tax']:>8,}")
    
    total = sum(s['total_payment'] for s in settlements)
    print(f"\n총 지급액: {total:,}원 | 총 인원: {len(settlements)}명")

if __name__ == '__main__':
    main()
