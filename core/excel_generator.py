"""
AutoTax — 엑셀 생성기
plan.md §9.1 홈택스 간이지급명세서 11컬럼 엑셀 양식 + 기안용 양식
"""
import os
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter

from db.repository import Repository
from core.crypto import CryptoManager
import csv


# ─────────────────────────────────────────────
# 홈택스 간이지급명세서 엑셀 (plan.md §9.1)
# ─────────────────────────────────────────────

HOMETAX_HEADERS = [
    '일련번호', '귀속연도', '귀속월', '업종코드', '소득자성명',
    '주민등록번호', '내외국인', '지급액', '세율', '소득세', '지방소득세'
]


def generate_hometax_excel(
    repo: Repository,
    crypto: CryptoManager,
    period: str,
    output_dir: str = None,
) -> str:
    """
    홈택스 간이지급명세서(사업소득) 엑셀 파일 생성.
    plan.md §9.1 — 정확히 11컬럼(A~K) 양식.

    Args:
        repo: Repository 인스턴스
        crypto: CryptoManager (주민번호 복호화용)
        period: 'YYYY-MM'
        output_dir: 저장 디렉토리 (None이면 프로젝트 루트)

    Returns:
        생성된 파일 경로
    """
    settlements = repo.get_settlements_by_period(period)
    if not settlements:
        raise ValueError(f'{period} 기간에 정산 데이터가 없습니다.')

    year, month = period.split('-')

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(output_dir, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = '간이지급명세서'

    # 헤더 스타일
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(start_color='D9E2F3', end_color='D9E2F3', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # 헤더 행
    for col, header in enumerate(HOMETAX_HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center')

    # 데이터 행
    for idx, s in enumerate(settlements, 1):
        row = idx + 1

        # 주민번호 복호화
        try:
            rid = crypto.decrypt(s['resident_id'])
        except Exception:
            rid = s.get('resident_id', '')

        # 주민번호 하이픈 형식 (홈택스 요구)
        if len(rid) == 13 and '-' not in rid:
            rid_formatted = f'{rid[:6]}-{rid[6:]}'
        else:
            rid_formatted = rid

        values = [
            idx,                    # A: 일련번호
            year,                   # B: 귀속연도
            month,                  # C: 귀속월
            s['industry_code'],     # D: 업종코드
            s.get('name', ''),      # E: 소득자성명
            rid_formatted,          # F: 주민등록번호
            s['is_foreigner'],      # G: 내외국인
            s['total_payment'],     # H: 지급액
            s['tax_rate'],          # I: 세율
            s['final_income_tax'],  # J: 소득세
            s['final_local_tax'],   # K: 지방소득세
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=row, column=col, value=val)
            cell.border = thin_border
            # 숫자 우측 정렬
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal='right')
                cell.number_format = '#,##0'
            else:
                cell.alignment = Alignment(horizontal='center')

    # 열 너비 자동 조정
    col_widths = [8, 10, 8, 10, 15, 18, 10, 15, 8, 15, 15]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # 파일명: 1000건 초과 시 분할 (plan.md §6.2)
    filename = f'간이지급명세서_{period}.xlsx'
    filepath = os.path.join(output_dir, filename)

    wb.save(filepath)
    wb.save(filepath)
    return filepath


def generate_hometax_csv(
    repo: Repository,
    crypto: CryptoManager,
    period: str,
    output_dir: str = None,
) -> str:
    """
    홈택스 간이지급명세서(사업소득) CSV 파일 생성.
    사용자 요청에 따라 변환파일 제출용으로 CSV를 생성합니다.
    """
    settlements = repo.get_settlements_by_period(period)
    if not settlements:
        raise ValueError(f'{period} 기간에 정산 데이터가 없습니다.')

    year, month = period.split('-')

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(output_dir, exist_ok=True)

    filename = f'간이지급명세서_{period}.csv'
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(HOMETAX_HEADERS)

        for idx, s in enumerate(settlements, 1):
            try:
                rid = crypto.decrypt(s['resident_id'])
            except Exception:
                rid = s.get('resident_id', '')

            if len(rid) == 13 and '-' not in rid:
                rid_formatted = f'{rid[:6]}-{rid[6:]}'
            else:
                rid_formatted = rid

            values = [
                idx,
                year,
                month,
                s['industry_code'],
                s.get('name', ''),
                rid_formatted,
                s['is_foreigner'],
                s['total_payment'],
                s['tax_rate'],
                s['final_income_tax'],
                s['final_local_tax'],
            ]
            writer.writerow(values)

    return filepath


# ─────────────────────────────────────────────
# 기안용 강사료 지급내역 엑셀 (prototype.html 양식)
# ─────────────────────────────────────────────

CUSTOM_HEADERS = [
    '연번', '프로그램', '강사', '산출근거(1회강사료)',
    '산출근거(강의횟수)', '강사료', '세액(소득세)',
    '세액(주민세)', '세액(합계)', '실지급액', '계좌번호'
]


def generate_custom_excel(
    repo: Repository,
    period: str,
    category_filter: str = None,
    output_dir: str = None,
) -> str:
    """
    기안용 강사료 지급내역 엑셀 생성.
    plan.md §10.5 + prototype.html generateCustomLectureExcel() 이식.

    Args:
        repo: Repository
        period: 'YYYY-MM'
        category_filter: 과목구분 필터 (None이면 전체)
        output_dir: 저장 디렉토리

    Returns:
        생성된 파일 경로
    """
    from core.tax_calculator import calculate_taxes, get_tax_rate

    lectures = repo.get_lectures_by_period(period)
    if not lectures:
        raise ValueError(f'{period} 기간에 강의 데이터가 없습니다.')

    # 필터 적용
    if category_filter:
        lectures = [l for l in lectures
                    if l.get('program_category', '') == category_filter]

    year, month = period.split('-')
    cat_label = category_filter or '전체과목'

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(output_dir, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = '기안용 강의내역'

    # 타이틀 행
    title_text = f'{year}년  {int(month)}월 {cat_label} 강사료 지급내역'
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=11)
    title_cell = ws.cell(row=1, column=1, value=title_text)
    title_cell.font = Font(bold=True, size=14)
    title_cell.alignment = Alignment(horizontal='center', vertical='center')

    # 빈 행
    # 단위 행
    ws.merge_cells(start_row=3, start_column=1, end_row=3, end_column=11)
    unit_cell = ws.cell(row=3, column=1, value='(단위 : 원)')
    unit_cell.alignment = Alignment(horizontal='right')
    unit_cell.font = Font(size=9)

    # 헤더
    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for col, header in enumerate(CUSTOM_HEADERS, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center', wrap_text=True)

    # 데이터
    data_row = 5
    for idx, lec in enumerate(lectures, 1):
        total = lec['payment_amount']
        rate = get_tax_rate(lec['industry_code'])
        taxes = calculate_taxes(total, rate)
        total_tax = taxes['income_tax'] + taxes['local_tax']

        # 계좌정보
        bank = lec.get('bank_name', '') or ''
        account = lec.get('account_number', '') or ''
        bank_info = f'{bank} {account}'.strip() if bank or account else ''

        values = [
            idx,
            lec.get('program_name', ''),
            lec.get('instructor_name', ''),
            lec['fee_per_session'],
            lec['session_count'],
            total,
            taxes['income_tax'],
            taxes['local_tax'],
            total_tax,
            taxes['net_payment'],
            bank_info,
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=data_row, column=col, value=val)
            cell.border = thin_border
            if isinstance(val, (int, float)) and col > 1:
                cell.alignment = Alignment(horizontal='right')
                cell.number_format = '#,##0'
            elif col == 1:
                cell.alignment = Alignment(horizontal='center')

        data_row += 1

    # 열 너비
    col_widths = [6, 18, 10, 14, 10, 14, 12, 12, 12, 14, 20]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    filename = f'강사료_지급내역_{period}.xlsx'
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    return filepath


# ─────────────────────────────────────────────
# 연간 거주자 사업소득 지급명세서 (prototype.html 양식)
# ─────────────────────────────────────────────

def generate_annual_excel(
    repo: Repository,
    crypto: CryptoManager,
    year: str,
    months: list[str] = None,
    output_dir: str = None,
) -> str:
    """
    연간 거주자 사업소득 지급명세서 엑셀 생성.

    Args:
        repo: Repository
        crypto: CryptoManager
        year: '2026'
        months: 선택 월 리스트 (None이면 전체)
        output_dir: 저장 디렉토리

    Returns:
        생성된 파일 경로
    """
    data = repo.get_annual_summary(year, months)
    if not data:
        raise ValueError(f'{year}년에 정산 데이터가 없습니다.')

    if output_dir is None:
        output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(output_dir, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = '연간거주자사업소득'

    headers = [
        '주민번호', '강사명', '업종코드',
        '연간 총지급액', '연간 총소득세', '연간 총지방소득세', '연간 총실지급액'
    ]

    header_font = Font(bold=True, size=10)
    header_fill = PatternFill(start_color='FCE4D6', end_color='FCE4D6', fill_type='solid')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.border = thin_border
        cell.alignment = Alignment(horizontal='center')

    for idx, row_data in enumerate(data, 2):
        # 주민번호 복호화
        try:
            rid = crypto.decrypt(row_data['resident_id'])
        except Exception:
            rid = row_data.get('resident_id', '')

        if len(rid) == 13 and '-' not in rid:
            rid = f'{rid[:6]}-{rid[6:]}'

        values = [
            rid,
            row_data.get('name', ''),
            row_data.get('industry_code', ''),
            row_data.get('annual_total', 0),
            row_data.get('annual_income_tax', 0),
            row_data.get('annual_local_tax', 0),
            row_data.get('annual_net_payment', 0),
        ]

        for col, val in enumerate(values, 1):
            cell = ws.cell(row=idx, column=col, value=val)
            cell.border = thin_border
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal='right')
                cell.number_format = '#,##0'

    col_widths = [18, 12, 10, 16, 16, 16, 16]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    month_label = '_'.join(months) if months else '전체'
    filename = f'연간거주자사업소득지급명세서_{year}_{month_label}.xlsx'
    filepath = os.path.join(output_dir, filename)
    wb.save(filepath)
    return filepath
