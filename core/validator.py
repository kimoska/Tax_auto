"""
AutoTax — 입력값 검증기
주민번호 형식 검증, 업종코드 유효성 확인
plan.md §9.3 업종코드 전체 목록 기반
"""
import re


# 유효한 업종코드 전체 목록 (plan.md §9.3)
VALID_INDUSTRY_CODES = {
    '940100', '940200', '940301', '940302', '940303', '940304', '940305', '940306',
    '940500', '940600',
    '940901', '940902', '940903', '940904', '940905', '940906', '940907', '940908',
    '940909', '940910', '940911', '940912', '940913', '940914', '940915', '940916',
    '940917', '940918', '940919', '940920', '940921', '940922', '940923', '940924',
    '940925', '940926', '940927', '940928', '940929',
    '851101',
}

# 업종코드 → 업종명 매핑 (prototype.html의 드롭다운 참조)
INDUSTRY_CODE_NAMES = {
    '940100': '저술가',
    '940200': '화가관련',
    '940301': '작곡가',
    '940302': '배우',
    '940303': '모델',
    '940304': '가수',
    '940305': '성악가',
    '940306': '1인미디어 콘텐츠창작자',
    '940500': '연예보조',
    '940600': '자문·고문',
    '940901': '바둑기사',
    '940902': '꽃꽂이교사',
    '940903': '학원강사',
    '940904': '직업운동가',
    '940905': '봉사료수취자',
    '940906': '보험설계',
    '940907': '음료배달',
    '940908': '방판·외판',
    '940909': '기타자영업',
    '940910': '다단계판매',
    '940911': '기타모집수당',
    '940912': '간병인',
    '940913': '대리운전',
    '940914': '캐디',
    '940915': '목욕관리사',
    '940916': '행사도우미',
    '940917': '심부름용역',
    '940918': '퀵서비스',
    '940919': '물품배달',
    '940920': '학습지방문강사',
    '940921': '교육교구방문강사',
    '940922': '대여제품방문점검원',
    '940923': '대출모집인',
    '940924': '신용카드회원모집인',
    '940925': '방과후강사',
    '940926': '소프트웨어프리랜서',
    '940927': '관광통역안내사',
    '940928': '어린이통학버스기사',
    '940929': '중고자동차판매원',
    '851101': '병의원',
}


def normalize_resident_id(rid: str) -> str:
    """
    주민번호 정규화: 하이픈 제거, 공백 제거.
    '800101-1234567' → '8001011234567'
    """
    return re.sub(r'[\s\-]', '', rid)


def validate_resident_id(rid: str) -> tuple[bool, str]:
    """
    주민번호 형식 검증.

    Returns:
        (is_valid, error_message)
        is_valid=True면 error_message는 빈 문자열
    """
    normalized = normalize_resident_id(rid)

    if not normalized:
        return False, "주민등록번호를 입력하세요."

    if len(normalized) != 13:
        return False, f"주민등록번호는 13자리여야 합니다. (현재 {len(normalized)}자리)"

    if not normalized.isdigit():
        return False, "주민등록번호는 숫자만 포함해야 합니다."

    # 앞 6자리: 생년월일 기본 범위 검증
    month = int(normalized[2:4])
    day = int(normalized[4:6])
    if month < 1 or month > 12:
        return False, "주민등록번호의 월(月)이 유효하지 않습니다."
    if day < 1 or day > 31:
        return False, "주민등록번호의 일(日)이 유효하지 않습니다."

    # 7번째 자리: 성별 코드 (1~4: 내국인, 5~8: 외국인)
    gender_code = int(normalized[6])
    if gender_code < 1 or gender_code > 8:
        return False, "주민등록번호 7번째 자리(성별코드)가 유효하지 않습니다."

    return True, ""


def validate_industry_code(code: str) -> tuple[bool, str]:
    """
    업종코드 유효성 검증.

    Returns:
        (is_valid, error_message)
    """
    if not code:
        return False, "업종코드를 선택하세요."

    if code not in VALID_INDUSTRY_CODES:
        return False, f"유효하지 않은 업종코드입니다: {code}"

    return True, ""


def get_industry_code_name(code: str) -> str:
    """업종코드 → 업종명 반환"""
    return INDUSTRY_CODE_NAMES.get(code, '알 수 없음')


def validate_period(period: str) -> tuple[bool, str]:
    """
    귀속연월 형식 검증 ('YYYY-MM').

    Returns:
        (is_valid, error_message)
    """
    if not period:
        return False, "귀속연월을 입력하세요."

    pattern = re.compile(r'^\d{4}-(0[1-9]|1[0-2])$')
    if not pattern.match(period):
        return False, "귀속연월 형식이 올바르지 않습니다. (예: 2026-03)"

    return True, ""
