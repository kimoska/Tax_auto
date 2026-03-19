# AutoTax 종합 구현 계획서 v3.1

> **Version**: 4.0 | **갱신일**: 2026-03-12  
> **v4.0 변경**: 소득유형 구분 폐기 → 업종코드 단일 관리, 1강사 다(多)프로그램 구조, 홈택스 공식 엑셀 양식 11컬럼 확정, 세액 자동계산·자동합산, 모든 입력항목 수정 버튼 필수화  
> **아키텍처 확정**: 100% 독립형 Python 데스크톱 애플리케이션 (외부 시스템 연동 없음)  
> **핵심 전략**: 강사·프로그램 등록 → 월별 강의횟수 입력 → 강사료·세액 자동계산 → 홈택스 엑셀 자동 생성 → RPA 파일 업로드  
> **폐기 사항**: 소득유형(사업/기타) 구분  폐기 · 홈택스 UI 건별 타이핑 RPA  완전 폐기

---

## 1. 기술 스택 최종 확정

| 레이어 | 기술 | 사유 |
|--------|------|------|
| **언어** | Python 3.11+ | 데이터 처리·엑셀·GUI·RPA 모두 단일 언어 |
| **GUI 기반** | PySide6 (Qt 6) | 상용급 데스크톱 프레임워크, LGPL 라이선스, Qt Designer 통합 |
| **GUI 디자인** | PyQt-Fluent-Widgets | Windows 11 Fluent Design, Mica/Acrylic 효과, 다크/라이트 테마, NavigationBar 내장 |
| **타이포그래피** | Pretendard (내장) | 한글/영문 외관 통일, 9개 웨이트, SIL Open Font License |
| **데이터베이스** | SQLite 3 | 내장형, 설치 불필요, `.db` 파일 하나로 관리 |
| **ORM** | 직접 SQL (sqlite3 내장) | 테이블 수 적어 ORM 불필요, 명시적 제어 |
| **엑셀 처리** | openpyxl + pandas | 홈택스 양식 복제·데이터 삽입 |
| **RPA** | Playwright (headed) | 브라우저 자동화, headless 불가(보안프로그램) |
| **네이티브 창 제어** | pywinauto (1순위) + pyautogui (최후보루) | 인증서 팝업: 창 핸들 제어 → 이미지 매칭 팔백 |
| **암호화** | cryptography (Fernet) | 주민번호·인증서 비밀번호 AES 암호화 |
| **배포** | PyInstaller → `.exe` | 더블클릭 실행, 설치 과정 없음 |
| **테스트** | pytest | 세액 계산·합산·엑셀 생성 단위 테스트 |

### 1.1 UI 프레임워크 선정 근거

| 후보 | 장점 | 단점 | 판정 |
|------|------|------|------|
| **CustomTkinter** | 간단, 빠른 프로토타입 | 투박한 디자인, 인디케이터/스피너 없음, 상용 수준 불가 |  탈락 |
| **Flet (Flutter)** | 모던 UI, 크로스 플랫폼 | 대량 테이블 성능 이슈, 복잡 UI 시 저하 |  부적합 |
| **PySide6 + Fluent** | Windows 11 Mica/Acrylic, ProgressRing, CardWidget, 다크모드, 상용 수준 | 학습 곡선 높음 |  **최종 채택** |

> **선정 근거**: 세무/금융 프로그램은 **신뢰감과 전문성**이 최우선. PyQt-Fluent-Widgets는 Windows 11의 네이티브 Fluent Design을 그대로 구현하여 사용자에게 한국 정부/금융기관 수준의 신뢰감을 줄 수 있음. Mica 배경 효과, Acrylic 블러, 내장 ProgressRing/InfoBar 등으로 별도 커스텀 없이도 상용화 수준 UI 구현 가능.

---

## 2. 프로젝트 디렉토리 구조

```
AutoTax/
├── main.py                          # 앱 진입점 (CustomTkinter 초기화)
├── requirements.txt                 # pip 의존성 목록
├── autotax.db                       # SQLite 데이터베이스 (gitignore)
├── .secret_key                      # Fernet 암호화 키 (gitignore)
│
├── db/
│   ├── __init__.py
│   ├── schema.py                    # CREATE TABLE DDL + 마이그레이션
│   ├── connection.py                # SQLite 커넥션 관리 (싱글턴)
│   └── repository.py               # 전 테이블 CRUD 함수 모음
│
├── core/
│   ├── __init__.py
│   ├── tax_calculator.py            # 세액 계산 엔진 (3.3% / 8.8%)
│   ├── aggregator.py                # 동일 강사 합산 (주민번호 기준)
│   ├── excel_generator.py           # 홈택스 규격 엑셀 생성 (openpyxl)
│   ├── validator.py                 # 주민번호 체크섬, 필수값 검증
│   └── crypto.py                    # 주민번호 Fernet 암호화/복호화
│
├── gui/
│   ├── __init__.py
│   ├── app.py                       # 메인 윈도우 (FluentWindow) + NavigationBar
│   ├── instructor_tab.py            # [탭1] 강사관리 CRUD
│   ├── lecture_tab.py               # [탭2] 강의관리 (월별 로그)
│   ├── settlement_tab.py            # [탭3] 강사료관리(정산) 대시보드
│   ├── settings_tab.py              # [탭4] 환경설정 (기관정보, 인증, 암호화)
│   ├── rpa_progress_dialog.py       # RPA 진행 상태 다이얼로그 (Step Indicator)
│   ├── override_dialog.py           # Manual Override 모달
│   └── widgets.py                   # 공통 커스텀 위젯
│
├── assets/
│   ├── fonts/
│   │   ├── Pretendard-Regular.otf
│   │   ├── Pretendard-Medium.otf
│   │   ├── Pretendard-SemiBold.otf
│   │   └── Pretendard-Bold.otf
│   ├── icons/                       # SVG 아이콘 (각 탭, 상태 아이콘)
│   ├── images/                      # pyautogui 이미지 매칭 템플릿
│   │   ├── cert_password_field.png  #   인증서 비밀번호 입력란 스크린샷
│   │   └── cert_ok_button.png       #   확인 버튼 스크린샷
│   └── style/
│       └── theme_overrides.qss      # Fluent 기본 테마 위에 추가 QSS 오버라이드
│
├── rpa/
│   ├── __init__.py
│   ├── rpa_runner.py                # 전체 실행 오케스트레이터
│   ├── hometax_login.py             # 로그인 (인증서/간편인증)
│   ├── hometax_uploader.py          # 메뉴이동 + 엑셀업로드 + 제출
│   ├── exception_handler.py         # 홈택스 팝업/오류 감지 및 추출
│   └── screenshot_manager.py        # 단계별 스크린샷 + 접수증 저장
│
├── templates/
│   └── 간이지급명세서_사업소득.xlsx    # 홈택스 공식 엑셀 양식 원본
│
├── outputs/                         # 생성된 엑셀·스크린샷·접수증 저장
├── logs/                            # 실행 로그 (rpa.log, app.log)
│
└── tests/
    ├── test_tax_calculator.py       # 세액 계산 단위 테스트
    ├── test_aggregator.py           # 합산 로직 테스트
    ├── test_excel_generator.py      # 엑셀 생성 + Override 반영 테스트
    ├── test_validator.py            # 주민번호 검증 테스트
    └── fixtures/                    # 테스트용 더미 데이터
        └── sample_data.json
```

---

## 3. 데이터베이스 스키마 (SQLite)

### 3.1 테이블 정의

```sql
-- ① 강사 마스터
CREATE TABLE instructors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,             -- 강사명 (필수)
    resident_id     TEXT    NOT NULL,             -- 주민등록번호 Fernet 암호화 (필수)
    phone           TEXT,                         -- 연락처 (선택)
    email           TEXT,                         -- 이메일 (선택)
    address         TEXT,                         -- 주소 (선택)
    industry_code   TEXT    NOT NULL DEFAULT '940909',  -- 업종코드 (필수, 코드표 참조)
    is_foreigner    TEXT    NOT NULL DEFAULT '1', -- 내외국인 (1=내국인, 9=외국인)
    bank_name       TEXT,                         -- 은행명 (선택)
    account_number  TEXT,                         -- 계좌번호 암호화 (선택)
    memo            TEXT,                         -- 비고/메모 (선택)
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ①-2 강사별 프로그램 (1강사 N프로그램)
CREATE TABLE instructor_programs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id   INTEGER NOT NULL REFERENCES instructors(id) ON DELETE CASCADE,
    category        TEXT    NOT NULL,             -- 과목구분 (예: 사회교육프로그램, 특화프로그램 등 - 필수)
    program_name    TEXT    NOT NULL,             -- 프로그램명 (필수)
    department      TEXT,                         -- 담당부서
    fee_per_session INTEGER NOT NULL DEFAULT 0,   -- 회당 강사료 (원 단위)
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_programs_instructor ON instructor_programs(instructor_id);

-- ② 월별 강의/지급 내역
CREATE TABLE lectures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id   INTEGER NOT NULL REFERENCES instructors(id),
    program_id      INTEGER NOT NULL REFERENCES instructor_programs(id),  -- 프로그램 선택 (필수)
    period          TEXT    NOT NULL,  -- 'YYYY-MM' 귀속연월
    payment_month   TEXT    NOT NULL,  -- 'YYYY-MM' 지급월
    session_count   INTEGER NOT NULL DEFAULT 0,   -- 강의 횟수 (필수)
    fee_per_session INTEGER NOT NULL DEFAULT 0,   -- 회당 강사료 (등록 시점 스냅샷)
    payment_amount  INTEGER NOT NULL DEFAULT 0,   -- 자동계산: session_count × fee_per_session
    status          TEXT    NOT NULL DEFAULT '입력완료'
                    CHECK(status IN ('입력완료','정산완료','제출완료')),
    created_by      TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_lectures_period ON lectures(period);
CREATE INDEX idx_lectures_instructor ON lectures(instructor_id, period);
CREATE INDEX idx_lectures_program ON lectures(program_id);

-- ③ 정산 결과 (월별 아카이빙 핵심)
CREATE TABLE settlements (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    instructor_id   INTEGER NOT NULL REFERENCES instructors(id),
    period          TEXT    NOT NULL,  -- 'YYYY-MM' 귀속연월
    industry_code   TEXT    NOT NULL,  -- 업종코드
    is_foreigner    TEXT    NOT NULL DEFAULT '1',
    total_payment   INTEGER NOT NULL,  -- 합산 총 지급액
    tax_rate        INTEGER NOT NULL DEFAULT 3,   -- 세율 (%, 기본 3)

    -- 자동 계산 값
    calc_income_tax INTEGER NOT NULL,    -- 자동 소득세 = 지급액 × 세율%, 원단위 절사
    calc_local_tax  INTEGER NOT NULL,    -- 자동 지방소득세 = 소득세 × 10%, 원단위 절사
    calc_net_payment INTEGER NOT NULL,   -- 실지급액 = 지급액 - 소득세 - 지방소득세

    -- Manual Override 값 (NULL = 미수정, 숫자 = 수동 입력)
    ovr_income_tax  INTEGER DEFAULT NULL,
    ovr_local_tax   INTEGER DEFAULT NULL,
    ovr_reason      TEXT    DEFAULT NULL,
    ovr_at          TEXT    DEFAULT NULL,
    ovr_by          TEXT    DEFAULT NULL,

    -- ★ 최종 확정 값 (엑셀 생성 시 이 값만 사용) ★
    final_income_tax INTEGER NOT NULL,
    final_local_tax  INTEGER NOT NULL,
    final_net_payment INTEGER NOT NULL,  -- 최종 실지급액

    -- 제출 이력
    is_submitted    INTEGER NOT NULL DEFAULT 0,
    submitted_at    TEXT    DEFAULT NULL,
    excel_filename  TEXT    DEFAULT NULL,
    receipt_path    TEXT    DEFAULT NULL,

    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),

    UNIQUE(instructor_id, period)  -- 강사+월 중복 방지
);
CREATE INDEX idx_settlements_period ON settlements(period);
CREATE INDEX idx_settlements_instructor ON settlements(instructor_id, period);

-- ④ 감사 로그 (모든 수정/생성/제출 기록)
CREATE TABLE audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action          TEXT    NOT NULL,  -- OVERRIDE | GENERATE_EXCEL | SUBMIT_RPA | REVERT
    target_table    TEXT    NOT NULL,
    target_id       INTEGER,
    period          TEXT,
    before_json     TEXT,   -- JSON 직렬화
    after_json      TEXT,
    reason          TEXT,
    performed_by    TEXT,
    performed_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE INDEX idx_audit_period ON audit_logs(period);

-- ⑤ 환경설정 (Key-Value 저장소 + 암호화 대상 구분)
CREATE TABLE app_settings (
    key             TEXT PRIMARY KEY,
    value           TEXT NOT NULL,
    is_encrypted    INTEGER NOT NULL DEFAULT 0,  -- 1이면 Fernet 암호화된 값
    category        TEXT NOT NULL DEFAULT 'general',
    updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- 초기 데이터 (앱 첫 실행 시 schema.py에서 삽입)
INSERT OR IGNORE INTO app_settings (key, value, is_encrypted, category) VALUES
    ('org_name',        '',    0, 'organization'),   -- 복지관명
    ('org_biz_number',  '',    0, 'organization'),   -- 사업자등록번호
    ('org_representative','',  0, 'organization'),   -- 대표자명
    ('org_address',     '',    0, 'organization'),   -- 주소
    ('org_tax_office',  '',    0, 'organization'),   -- 관할세무서
    ('auth_method',     'certificate', 0, 'auth'),   -- certificate | simple_kakao | simple_naver
    ('cert_password',   '',    1, 'auth'),            -- ★ Fernet 암호화 저장 ★
    ('cert_path',       '',    0, 'auth'),            -- 인증서 경로 (NPKI)
    ('simple_auth_id',  '',    0, 'auth'),            -- 간편인증용 식별번호
    ('default_industry_code', '940909', 0, 'defaults');  -- 기본 업종코드
```

### 3.2 연간 신고 확장성

```sql
-- 연간 지급명세서 데이터 추출 (추후 구현 시 즉시 사용 가능)
SELECT
    s.instructor_id,
    i.name,
    s.industry_code,
    SUM(s.total_payment)      AS annual_total,
    SUM(s.final_income_tax)   AS annual_income_tax,
    SUM(s.final_local_tax)    AS annual_local_tax,
    SUM(s.final_net_payment)  AS annual_net_payment
FROM settlements s
JOIN instructors i ON s.instructor_id = i.id
WHERE s.period BETWEEN '2026-01' AND '2026-12'
GROUP BY s.instructor_id;
```

> `settlements`가 월별 1행이므로, 12개월 `SUM`으로 연간 합산 즉시 가능

---

## 4. Manual Override 데이터 파이프라인 (빈틈 없는 설계)

### 4.1 파이프라인 전체 흐름도

```
lectures 테이블           settlements 테이블            엑셀 파일
(개별 지급 건)             (강사별 월별 정산)             (홈택스 제출용)

┌────────────┐
│ 요가 300,000│──┐
│ 필라 200,000│──┤ GROUP BY
│ 서예 100,000│──┤ instructor_id
└────────────┘  │ + period
                ▼
        ┌───────────────┐
        │ total_payment  │ = 600,000
        │                │
        │ calc_income_tax│ = 18,000  ← TaxCalculator.calc()
        │ calc_local_tax │ = 1,800   ← 자동 계산
        │                │
        │ ovr_income_tax │ = NULL    ← 아직 수동 수정 없음
        │ ovr_local_tax  │ = NULL
        │                │
        │ ★ final 결정 로직: ★
        │ final_income_tax = COALESCE(ovr_income_tax, calc_income_tax)
        │ final_local_tax  = COALESCE(ovr_local_tax, calc_local_tax)
        │                │
        │ final_income_tax│ = 18,000  ← calc 값 사용
        │ final_local_tax │ = 1,800
        └───────┬───────┘
                │
                │ [관리자가 소득세를 20,000으로 수정]
                ▼
        ┌───────────────┐
        │ calc_income_tax│ = 18,000  ← 원본 보존 (불변)
        │ calc_local_tax │ = 1,800   ← 원본 보존 (불변)
        │                │
        │ ovr_income_tax │ = 20,000  ← 수동 입력값
        │ ovr_local_tax  │ = 2,000   ← 수동 입력값
        │ ovr_reason     │ = "단수차이 조정"
        │                │
        │ final_income_tax│ = 20,000 ← ★ ovr 우선 적용 ★
        │ final_local_tax │ = 2,000  ← ★ ovr 우선 적용 ★
        └───────┬───────┘
                │
                ▼ excel_generator.py
        ┌───────────────────────────────────┐
        │ 홈택스 엑셀 J열(소득세)  = 20,000  │ ← final_income_tax
        │ 홈택스 엑셀 K열(지방세) = 2,000   │ ← final_local_tax
        └───────────────────────────────────┘
```

### 4.2 final 값 결정 — 핵심 Python 코드

```python
# repository.py — settlement 저장/갱신 시 final 값 자동 결정

def upsert_settlement(self, instructor_id, period, calc_data, override=None):
    """정산 결과 저장. final 값은 override가 있으면 override, 없으면 calc 사용"""

    # ★ COALESCE 로직: override > calc ★
    final_income_tax = (override['income_tax'] if override and override.get('income_tax') is not None
                        else calc_data['income_tax'])
    final_local_tax  = (override['local_tax'] if override and override.get('local_tax') is not None
                        else calc_data['local_tax'])
    final_net_payment = calc_data['total_payment'] - final_income_tax - final_local_tax

    self.db.execute("""
        INSERT INTO settlements (
            instructor_id, period, industry_code, is_foreigner,
            total_payment, tax_rate,
            calc_income_tax, calc_local_tax, calc_net_payment,
            ovr_income_tax, ovr_local_tax, ovr_reason, ovr_at, ovr_by,
            final_income_tax, final_local_tax, final_net_payment
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instructor_id, period) DO UPDATE SET
            total_payment    = excluded.total_payment,
            calc_income_tax  = excluded.calc_income_tax,
            calc_local_tax   = excluded.calc_local_tax,
            calc_net_payment = excluded.calc_net_payment,
            -- ★ 재정산 시에도 기존 override 보존 ★
            ovr_income_tax   = COALESCE(settlements.ovr_income_tax, excluded.ovr_income_tax),
            ovr_local_tax    = COALESCE(settlements.ovr_local_tax, excluded.ovr_local_tax),
            -- ★ final은 항상 재계산 ★
            final_income_tax = COALESCE(settlements.ovr_income_tax, excluded.calc_income_tax),
            final_local_tax  = COALESCE(settlements.ovr_local_tax, excluded.calc_local_tax),
            final_net_payment = excluded.total_payment
                - COALESCE(settlements.ovr_income_tax, excluded.calc_income_tax)
                - COALESCE(settlements.ovr_local_tax, excluded.calc_local_tax),
            updated_at       = datetime('now','localtime')
    """, params)

def apply_override(self, settlement_id, income_tax, local_tax, reason, user):
    """수동 수정 적용 — final 값 즉시 갱신"""
    self.db.execute("""
        UPDATE settlements SET
            ovr_income_tax   = ?,
            ovr_local_tax    = ?,
            ovr_reason       = ?,
            ovr_at           = datetime('now','localtime'),
            ovr_by           = ?,
            final_income_tax = ?,    -- ★ ovr 값으로 final 즉시 덮어쓰기 ★
            final_local_tax  = ?,    -- ★ ovr 값으로 final 즉시 덮어쓰기 ★
            updated_at       = datetime('now','localtime')
        WHERE id = ?
    """, (income_tax, local_tax, reason, user,
          income_tax, local_tax,  # final = ovr
          settlement_id))

def revert_override(self, settlement_id):
    """수동 수정 되돌리기 — final을 calc로 복원"""
    self.db.execute("""
        UPDATE settlements SET
            ovr_income_tax   = NULL,
            ovr_local_tax    = NULL,
            ovr_reason       = NULL,
            ovr_at           = NULL,
            ovr_by           = NULL,
            final_income_tax = calc_income_tax,  -- ★ calc로 복원 ★
            final_local_tax  = calc_local_tax,   -- ★ calc로 복원 ★
            updated_at       = datetime('now','localtime')
        WHERE id = ?
    """, (settlement_id,))
```

### 4.3 엑셀 생성 시 final 값만 사용 (보장)

```python
# excel_generator.py

def generate_hometax_excel(self, period):
    settlements = self.repo.get_settlements_by_period(period)

    rows = []
    for idx, s in enumerate(settlements, 1):
        # ★ 홈택스 공식 엑셀 양식 11컬럼 (A~K) 순서 엄수 ★
        rows.append({
            'A_일련번호': idx,                                          # A열
            'B_귀속연도': period[:4],                                   # B열
            'C_귀속월': period[5:7],                                    # C열
            'D_업종코드': s['industry_code'],                          # D열
            'E_소득자성명': s['name'],                                  # E열
            'F_주민등록번호': self.crypto.decrypt(s['resident_id']),    # F열 (하이픈 없이 13자리)
            'G_내외국인': s['is_foreigner'],                          # G열 (내국인:1, 외국인:9) ← 홈택스 규격
            'H_지급액': s['total_payment'],                            # H열
            'I_세율': s['tax_rate'],                                   # I열 (3, 5, 20 중 택1)
            'J_소득세': s['final_income_tax'],                         # J열 ★ 반드시 final 사용 ★
            'K_지방소득세': s['final_local_tax']                       # K열 ★ 반드시 final 사용 ★
        })
    # ... openpyxl로 엑셀 파일 생성 (2행부터 데이터, 최대 1000행)
```

---

## 5. 상용화 디자인 시스템 (Design System)

> 이 섹션은 AutoTax의 전체 시각 언어를 정의한다.
> 목표: **B2B 세무 SaaS 수준의 신뢰감·전문성·미려함**

### 5.1 Color Palette (색상표)

금융/세무 프로그램에 적합한 **Deep Trust** 팔레트:

| 역할 | 이름 | HEX | 용도 |
|------|------|-----|------|
| **Primary** | Navy 900 | `#0F1B2D` | 사이드 NavigationBar 배경, 최상단 헤더 |
| **Primary Light** | Navy 700 | `#1B3A5C` | 호버 상태, 선택된 탭 강조 |
| **Surface** | Cool White | `#F8F9FB` | 메인 콘텐츠 영역 배경 (라이트 모드) |
| **Surface Dark** | Charcoal | `#1E1E2E` | 메인 콘텐츠 영역 배경 (다크 모드) |
| **Card** | Pure White | `#FFFFFF` | CardWidget 배경 (라이트), `#2A2A3D` (다크) |
| **Accent** | Royal Blue | `#2563EB` | 주요 CTA 버튼, 선택 강조, 링크 |
| **Accent Hover** | Deep Blue | `#1D4ED8` | 버튼 호버 시 |
| **Success** | Emerald | `#10B981` | 정산 완료, 제출 성공 상태 |
| **Warning** | Amber | `#F59E0B` | 수동 수정됨(Override) 상태 표시 |
| **Error** | Rose | `#EF4444` | 검증 오류, 실패 상태 |
| **Text Primary** | Ink Black | `#111827` | 본문 텍스트 (라이트) / `#E5E7EB` (다크) |
| **Text Secondary** | Slate | `#6B7280` | 부제목, 비활성 라벨 |
| **Border** | Mist Gray | `#E5E7EB` | 테이블 구분선, 입력 필드 테두리 |
| **Mica Effect** | — | 시스템 연동 | Windows 11 Mica: 바탕화면 색상이 반투명 반영 |

### 5.2 Typography (서체)

**Pretendard** 오픈소스 폰트를 앱에 내장(Embed)하여 어떤 PC에서도 동일한 외관 보장:

```python
# app.py — Pretendard 폰트 내장 로직

from PySide6.QtGui import QFontDatabase, QFont
import os

def load_pretendard_fonts(app):
    """앱 시작 시 Pretendard 폰트를 QFontDatabase에 등록"""
    font_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'fonts')
    weights = ['Regular', 'Medium', 'SemiBold', 'Bold']
    for weight in weights:
        font_path = os.path.join(font_dir, f'Pretendard-{weight}.otf')
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            print(f" 폰트 로드 실패: {font_path}")

    # 전체 앱 기본 폰트로 설정
    app.setFont(QFont("Pretendard", 10))
```

**서체 사용 가이드:**

| 용도 | 웨이트 | 크기 | 예시 |
|------|--------|------|------|
| **대제목** (탭 타이틀) | Bold (700) | 20px | "강사료관리 (정산)" |
| **섹션 제목** | SemiBold (600) | 16px | " 기관 기본 정보" |
| **테이블 헤더** | SemiBold (600) | 13px | "강사명 \| 소득구분 \| 지급액" |
| **본문/데이터** | Regular (400) | 13px | "홍길동", "500,000" |
| **라벨/캡션** | Medium (500) | 12px | "귀속연월:", "수정 사유*" |
| **숫자 강조** | Bold (700) | 14px | "₩ 26,400" (원천징수 합계) |
| **상태 뱃지** | SemiBold (600) | 11px | "입력완료", "제출완료" |

### 5.3 Component Style Guide (QSS)

#### 5.3.1 CardWidget (Fluent 기본 + 커스텀 그림자)

```css
/* theme_overrides.qss */

/* ── CardWidget: 부드러운 그림자 + 라운드 코너 ── */
CardWidget {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
    padding: 20px;
    /* QGraphicsDropShadowEffect로 Python에서 적용 */
}

/* 다크 모드 */
CardWidget[dark="true"] {
    background-color: #2A2A3D;
    border: 1px solid #3A3A4D;
}
```

```python
# widgets.py — CardWidget에 Drop Shadow 적용
from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

def apply_card_shadow(widget):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(20)
    shadow.setXOffset(0)
    shadow.setYOffset(4)
    shadow.setColor(QColor(0, 0, 0, 25))  # 10% 불투명 검정
    widget.setGraphicsEffect(shadow)
```

#### 5.3.2 PrimaryPushButton (호버 애니메이션)

```css
/* Fluent PrimaryPushButton 오버라이드 */
PrimaryPushButton {
    background-color: #2563EB;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 24px;
    font-family: "Pretendard";
    font-weight: 600;
    font-size: 13px;
}

PrimaryPushButton:hover {
    background-color: #1D4ED8;
    /* QPropertyAnimation으로 150ms ease-in-out 전환 */
}

PrimaryPushButton:pressed {
    background-color: #1E40AF;
}

PrimaryPushButton:disabled {
    background-color: #94A3B8;
}
```

```python
# widgets.py — 버튼 호버 애니메이션
from PySide6.QtCore import QPropertyAnimation, QEasingCurve

def setup_hover_animation(button):
    """버튼에 부드러운 배경색 전환 애니메이션 적용"""
    anim = QPropertyAnimation(button, b"backgroundColor")
    anim.setDuration(150)
    anim.setEasingCurve(QEasingCurve.InOutCubic)
    return anim
```

#### 5.3.3 Override 모달 (Glassmorphism / Acrylic 블러)

```python
# override_dialog.py — Acrylic 배경 모달

from qfluentwidgets import MessageBoxBase, SubtitleLabel, LineEdit, TextEdit
from qfluentwidgets import InfoBar, InfoBarPosition

class OverrideDialog(MessageBoxBase):
    """Manual Override 모달 — Fluent Acrylic 배경"""

    def __init__(self, settlement_data, parent=None):
        super().__init__(parent)
        self.titleLabel = SubtitleLabel("세액 수동 수정")

        # 자동 계산 값 (읽기 전용, 회색 배경)
        self.calc_tax_label = SubtitleLabel(
            f"자동 소득세: ₩{settlement_data['calc_income_tax']:,}")
        self.calc_tax_label.setStyleSheet("color: #6B7280; background: #F3F4F6; "
                                          "border-radius: 4px; padding: 8px;")

        # 수정 입력 필드
        self.income_tax_edit = LineEdit(self)
        self.income_tax_edit.setPlaceholderText("수정 소득세 (빈칸 시 자동값 유지)")

        self.local_tax_edit = LineEdit(self)
        self.local_tax_edit.setPlaceholderText("수정 지방소득세")

        self.reason_edit = TextEdit(self)
        self.reason_edit.setPlaceholderText("수정 사유를 반드시 입력하세요 *")

        # 레이아웃 구성
        self.viewLayout.addWidget(self.titleLabel)
        self.viewLayout.addWidget(self.calc_tax_label)
        self.viewLayout.addWidget(self.income_tax_edit)
        self.viewLayout.addWidget(self.local_tax_edit)
        self.viewLayout.addWidget(self.reason_edit)

        self.yesButton.setText("저장")
        self.cancelButton.setText("취소")
```

#### 5.3.4 상태 뱃지 (Status Badge)

```css
/* 상태 뱃지 — 색상으로 업무 단계 즉시 인식 */
.badge-pending {
    background-color: #DBEAFE;
    color: #1E40AF;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 11px;
    font-weight: 600;
}

.badge-complete {
    background-color: #D1FAE5;
    color: #065F46;
}

.badge-submitted {
    background-color: #E0E7FF;
    color: #3730A3;
}

.badge-overridden {
    background-color: #FEF3C7;
    color: #92400E;
}
```

### 5.4 앱 레이아웃 (FluentWindow + NavigationBar)

```python
# app.py — 메인 윈도우 (Fluent Design)

from qfluentwidgets import (FluentWindow, NavigationItemPosition,
                            FluentIcon as FIF, setTheme, Theme)

class AutoTaxWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoTax — 강사료 원천세 자동화")
        self.resize(1280, 800)
        self.setMinimumSize(1024, 700)

        # ──── Windows 11 Mica 효과 활성화 ────
        self.setMicaEffectEnabled(True)

        # ──── Pretendard 폰트 로드 ────
        load_pretendard_fonts(QApplication.instance())

        # ──── 탭(Sub-Interface) 등록 ────
        self.instructor_tab = InstructorTab(self)
        self.lecture_tab = LectureTab(self)
        self.settlement_tab = SettlementTab(self)
        self.annual_tab = AnnualTab(self)
        self.settings_tab = SettingsTab(self)

        self.addSubInterface(self.instructor_tab, FIF.PEOPLE,      "강사 관리")
        self.addSubInterface(self.lecture_tab,    FIF.EDUCATION,    "강의 내역")
        self.addSubInterface(self.settlement_tab, FIF.MONEY,        "월별 정산 (홈택스)")
        self.addSubInterface(self.annual_tab,     FIF.CALENDAR,     "연간 신고 데이터")

        # 환경설정은 NavigationBar 하단 고정
        self.addSubInterface(
            self.settings_tab, FIF.SETTING, "시스템 설정",
            position=NavigationItemPosition.BOTTOM
        )

        # ──── 다크/라이트 테마 토글 ────
        # setTheme(Theme.DARK)  # 또는 Theme.LIGHT
```

**결과 레이아웃:**

```
┌──────────────────────────────────────────────────────────────────────┐
│  ████ Mica 반투명 타이틀바 (바탕화면 색상 반영) ████                    │
├────────┬─────────────────────────────────────────────────────────────┤
│        │                                                             │
│ [탭 1] │  ┌─ CardWidget ────────────────────────────────────────┐    │
│ 강사   │  │ [검색 ________] [업종코드: 전체▼]  [+ 강사 등록]      │    │
│ 관리   │  └──────────────────────────────────────────────────────┘    │
│        │                                                             │
│ [탭 2] │  ┌─ CardWidget (테이블) ─────────────────────────────────┐  │
│ 강의   │  │ 강사명 │ 업종코드 │ 프로그램   │ 연락처   │ 관리        │  │
│ 내역   │  │ 홍길동 │ 940903   │ 요가(8만)  │ 010-...  │ [수정]      │  │
│        │  │ 김영희 │ 940903   │ 서예(6만)  │ 010-...  │ [수정]      │  │
│ [탭 3] │  └──────────────────────────────────────────────────────┘    │
│ 월별   │                                                             │
│ 정산   │  ┌─ Summary CardWidget ──────────────────────────────┐     │
│ ─────  │  │ 전체 강사: 15명  │  운영 프로그램: 28개             │     │
│ [탭 4] │  └──────────────────────────────────────────────────────┘    │
│ 연간   │                                                             │
│ 데이터 │                                                             │
│ ─────  │                                                             │
│ [설정] │                                                             │
│ 시스템 │                                                             │
├────────┴─────────────────────────────────────────────────────────────┤
│  AutoTax v1.0                                          Theme: Dark   │
└──────────────────────────────────────────────────────────────────────┘
```

### 5.5 RPA 진행 상태 다이얼로그 (Step Indicator)

RPA 실행(10초~수 분) 동안 화면이 멈추지 않도록 **비동기 워커 스레드 + 시각적 Progress UI** 설계:

```python
# rpa_progress_dialog.py — RPA 실행 상태 표시 다이얼로그

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget
from qfluentwidgets import (ProgressRing, StrongBodyLabel, BodyLabel,
                            InfoBar, InfoBarPosition, CardWidget,
                            IndeterminateProgressRing)

class RPAWorkerThread(QThread):
    """RPA를 별도 스레드에서 실행 (GUI 프리징 방지)"""
    step_changed = Signal(int, str)    # (step_index, step_description)
    step_completed = Signal(int, bool) # (step_index, is_success)
    all_done = Signal(bool, str)       # (overall_success, message)

    def run(self):
        import asyncio
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(self._run_rpa())
        self.all_done.emit(result.success, result.error_message or "")

    async def _run_rpa(self):
        runner = RPARunner(repo=self.repo, crypto=self.crypto)
        runner.on_step_change = lambda i, desc: self.step_changed.emit(i, desc)
        runner.on_step_done = lambda i, ok: self.step_completed.emit(i, ok)
        return await runner.run(self.period, self.excel_path)


class RPAProgressDialog(QWidget):
    """
    RPA 실행 중 표시되는 Step Indicator 다이얼로그

    ┌──────────────────────────────────────────────────┐
    │  홈택스 자동 제출 진행 중                          │
    │                                                  │
    │   - -- - -- - -- - -- - -- -                       │
    │                                                  │
    │   [완료] Step 1. 사전 조건 확인                    │
    │   [진행] Step 2. 홈택스 로그인 중...               │
    │   [대기] Step 3. 메뉴 이동                         │
    │   [대기] Step 4. 엑셀 파일 업로드                  │
    │   [대기] Step 5. 검증 결과 확인                    │
    │   [대기] Step 6. 최종 제출 & 접수증                │
    │                                                  │
    │   (ProgressRing 스피너)                            │
    │                                                  │
    │   경과 시간: 00:23                                │
    │   [취소]                                          │
    └──────────────────────────────────────────────────┘
    """

    STEPS = [
        "사전 조건 확인",
        "홈택스 로그인",
        "메뉴 이동",
        "엑셀 파일 업로드",
        "검증 결과 확인",
        "최종 제출 & 접수증 저장"
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(480, 520)
        layout = QVBoxLayout(self)

        # 제목
        self.title = StrongBodyLabel("홈택스 자동 제출 진행 중")

        # 스텝 라벨 목록
        self.step_labels = []
        for i, step_name in enumerate(self.STEPS):
            label = BodyLabel(f"[대기] Step {i+1}. {step_name}")
            label.setStyleSheet("color: #6B7280; padding: 4px 0;")
            self.step_labels.append(label)
            layout.addWidget(label)

        # Fluent ProgressRing (스피너)
        self.spinner = IndeterminateProgressRing(self)
        self.spinner.setFixedSize(48, 48)
        layout.addWidget(self.spinner)

        # 경과 시간
        self.elapsed_label = BodyLabel("경과 시간: 00:00")

    def on_step_changed(self, step_index, description):
        """현재 진행 중인 스텝 업데이트"""
        for i, label in enumerate(self.step_labels):
            if i < step_index:
                label.setText(f"[완료] Step {i+1}. {self.STEPS[i]}")
                label.setStyleSheet("color: #059669; font-weight: 600;")
            elif i == step_index:
                label.setText(f"[진행] Step {i+1}. {description}...")
                label.setStyleSheet("color: #2563EB; font-weight: 700;")
            else:
                label.setText(f"[대기] Step {i+1}. {self.STEPS[i]}")
                label.setStyleSheet("color: #6B7280;")

    def on_step_failed(self, step_index, error_msg):
        """스텝 실패 시"""
        self.step_labels[step_index].setText(
            f"[실패] Step {step_index+1}. {self.STEPS[step_index]} — 실패")
        self.step_labels[step_index].setStyleSheet(
            "color: #DC2626; font-weight: 700;")
        self.spinner.hide()

        # Fluent InfoBar로 오류 알림
        InfoBar.error(
            title="RPA 오류",
            content=error_msg,
            position=InfoBarPosition.TOP,
            parent=self.parent()
        )

    def on_all_complete(self, success):
        """전체 완료"""
        self.spinner.hide()
        if success:
            self.title.setText("홈택스 자동 제출 완료!")
            InfoBar.success(
                title="제출 완료",
                content="간이지급명세서가 정상적으로 제출되었습니다.",
                position=InfoBarPosition.TOP,
                parent=self.parent()
            )
```

### 5.6 [탭4] 환경설정

(설정 UI 레이아웃 및 로직은 v2.1에서 설계한 것과 동일 — Fluent의 `CardWidget` + `LineEdit` + `RadioButton` 사용)

**주요 변경: Fluent 위젯으로 교체**

```python
# settings_tab.py — Fluent 위젯으로 환경설정 구현

from qfluentwidgets import (ScrollArea, CardWidget, LineEdit, PasswordLineEdit,
                            RadioButton, ComboBox, PrimaryPushButton,
                            SubtitleLabel, CaptionLabel, InfoBar)

class SettingsTab(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsTab")

        # ── 기관 정보 카드 ──
        org_card = CardWidget(self)
        org_card_title = SubtitleLabel("기관 기본 정보")
        self.org_name = LineEdit(self); self.org_name.setPlaceholderText("기관명 (예: 대치노인복지관)")
        self.biz_number = LineEdit(self); self.biz_number.setPlaceholderText("사업자등록번호 (예: 123-45-67890)")
        self.org_representative = LineEdit(self); self.org_representative.setPlaceholderText("대표자명")
        self.org_tax_office = LineEdit(self); self.org_tax_office.setPlaceholderText("관할 세무서 (예: 삼성세무서)")
        self.org_address = LineEdit(self); self.org_address.setPlaceholderText("사업장 주소")
        # ... 레이아웃 추가 코드

        # ── 인증 설정 카드 ──
        auth_card = CardWidget(self)
        self.auth_cert = RadioButton("공동인증서", self)
        self.auth_kakao = RadioButton("간편인증 (카카오)", self)
        self.auth_naver = RadioButton("간편인증 (네이버)", self)

        # 인증서 경로 및 비밀번호 필드
        self.cert_path = LineEdit(self)
        self.cert_path.setPlaceholderText("NPKI 인증서 폴더 경로 (예: C:\\...\\NPKI\\...)")
        self.cert_password = PasswordLineEdit(self)
        self.cert_password.setPlaceholderText("인증서 비밀번호 (암호화 저장)")
        CaptionLabel("AES-256(Fernet) 암호화되어 로컬에 저장됩니다.", self)

        # ── 저장 버튼 ──
        self.save_btn = PrimaryPushButton("설정 저장", self)
        self.save_btn.clicked.connect(self.save_settings)

    def save_settings(self):
        """암호화 대상 필드는 Fernet 암호화 후 DB 저장"""
        pw = self.cert_password.text()
        if pw:
            encrypted = self.crypto.encrypt(pw)
            self.repo.update_setting('cert_password', encrypted)
        # ... 나머지 설정값 저장
```

---

## 6. RPA 예외 처리 강화 워크플로우

### 6.1 전체 실행 흐름 (모든 단계에 Try-Catch + Explicit Wait)

```python
# rpa_runner.py — 핵심 오케스트레이션 (예외 처리 강화 버전)

class RPARunner:
    TIMEOUT_LOGIN   = 30_000   # 로그인 완료 대기
    TIMEOUT_AUTH    = 180_000  # 간편인증 모바일 승인 대기
    TIMEOUT_UPLOAD  = 60_000   # 엑셀 업로드 처리 대기
    TIMEOUT_SUBMIT  = 30_000   # 제출 처리 대기
    TIMEOUT_ELEMENT = 10_000   # 일반 요소 출현 대기

    async def run(self, period: str, excel_paths: list[str], auth_method='certificate'):
        """
        ★ v3.1: excel_path(str) → excel_paths(list) 로 변경
        1000건 초과 시 엑셀이 분할되므로, 모든 파일을 순차 업로드 후 최종 제출 1회 수행
        """
        result = RPAResult(period=period)

        async with async_playwright() as p:
            browser = None
            page = None
            try:
                # ── Step 0: 사전 조건 (모든 파일 존재 확인) ──
                for ep in excel_paths:
                    if not os.path.exists(ep):
                        raise RPAError("PRECONDITION", f"엑셀 파일 없음: {ep}")

                browser = await p.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                page = await browser.new_page()

                # ── Step 1: 로그인 ──
                try:
                    await self._step_login(page, auth_method)
                    result.log("LOGIN", "SUCCESS", "로그인 성공")
                except Exception as e:
                    await self._capture_and_log(page, result, "LOGIN", str(e))
                    raise RPAError("LOGIN", str(e))

                # ── Step 2: 메뉴 이동 ──
                try:
                    await self._step_navigate(page)
                    result.log("NAVIGATE", "SUCCESS", "메뉴 이동 완료")
                except Exception as e:
                    await self._capture_and_log(page, result, "NAVIGATE", str(e))
                    raise RPAError("NAVIGATE", str(e))

                # ── Step 3: 엑셀 업로드 (★ v3.1: 다중 파일 반복 업로드) ──
                try:
                    for file_idx, ep in enumerate(excel_paths):
                        result.log("UPLOAD", "PROGRESS",
                                   f"파일 {file_idx+1}/{len(excel_paths)} 업로드 중: {os.path.basename(ep)}")
                        upload_result = await self._step_upload(page, ep)
                        result.log("UPLOAD", "SUCCESS",
                                   f"파일 {file_idx+1} 업로드 완료: {upload_result}")
                        if file_idx < len(excel_paths) - 1:
                            # 다음 파일 업로드를 위해 [일괄등록] 버튼으로 다시 이동
                            await page.wait_for_timeout(2000)
                except HometaxValidationError as e:
                    await self._capture_and_log(page, result, "UPLOAD_VALIDATION", str(e))
                    result.validation_errors = e.errors
                    raise
                except Exception as e:
                    await self._capture_and_log(page, result, "UPLOAD", str(e))
                    raise RPAError("UPLOAD", str(e))

                # ── Step 4: 최종 제출 ──
                try:
                    await self._step_submit(page)
                    result.log("SUBMIT", "SUCCESS", "제출 완료")
                except Exception as e:
                    await self._capture_and_log(page, result, "SUBMIT", str(e))
                    raise RPAError("SUBMIT", str(e))

                # ── Step 5: 접수증 저장 ──
                try:
                    await self._step_save_receipt(page, period)
                    result.log("RECEIPT", "SUCCESS", "접수증 저장 완료")
                except Exception as e:
                    # 접수증 저장 실패는 치명적이지 않음 → 경고만
                    result.log("RECEIPT", "WARNING", f"접수증 저장 실패: {e}")

                result.success = True

            except RPAError as e:
                result.success = False
                result.error_step = e.step
                result.error_message = str(e)
                logger.error(f"RPA 실패 [{e.step}]: {e}")

            except Exception as e:
                result.success = False
                result.error_message = f"예상치 못한 오류: {e}"
                if page:
                    await self._capture_and_log(page, result, "UNKNOWN", str(e))

            finally:
                # ★ 어떤 상황에서도 브라우저 정리 ★
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass

                # 결과 로그 파일 저장
                result.save_to_file(f"logs/rpa_{period}.json")

            return result
```

### 6.2 홈택스 팝업/오류 감지 전용 모듈

```python
# exception_handler.py — 홈택스 특유의 오류 팝업 감지 및 텍스트 추출

class HometaxExceptionHandler:
    """홈택스 환경의 모든 예외 상황을 감지하고 내용을 추출"""

    # 홈택스에서 발생 가능한 오류 팝업 셀렉터 목록
    ERROR_SELECTORS = [
        'div.alert_layer',                    # 일반 알림 레이어
        'div.popup_wrap:has-text("오류")',     # 오류 팝업
        'div.popup_wrap:has-text("에러")',     # 에러 팝업
        'div.err_area',                        # 검증 오류 영역
        'table.errList',                       # 업로드 오류 목록 테이블
        'div[class*="error"]',                 # 클래스에 error 포함
        '.ui-dialog:visible',                  # jQuery UI 다이얼로그
    ]

    CONFIRM_SELECTORS = [
        'button:has-text("확인")',
        'input[value="확인"]',
        'a:has-text("닫기")',
    ]

    async def check_for_errors(self, page) -> list[str]:
        """현재 페이지에서 오류 팝업/메시지 존재 여부 확인 + 텍스트 추출"""
        errors = []
        for selector in self.ERROR_SELECTORS:
            try:
                elements = await page.query_selector_all(selector)
                for el in elements:
                    if await el.is_visible():
                        text = await el.text_content()
                        if text and text.strip():
                            errors.append(text.strip())
            except:
                continue
        return errors

    async def dismiss_popup(self, page):
        """오류/알림 팝업이 있으면 [확인]/[닫기] 클릭하여 닫기"""
        for selector in self.CONFIRM_SELECTORS:
            try:
                btn = await page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1000)
                    return True
            except:
                continue
        return False

    async def extract_upload_errors(self, page) -> list[dict]:
        """엑셀 업로드 후 홈택스 검증 오류 테이블의 행별 오류 추출"""
        errors = []
        try:
            rows = await page.query_selector_all('table.errList tr, .upload_err_list tr')
            for row in rows:
                cells = await row.query_selector_all('td')
                if len(cells) >= 2:
                    line_no = await cells[0].text_content()
                    err_msg = await cells[1].text_content()
                    errors.append({
                        'line': line_no.strip(),
                        'message': err_msg.strip()
                    })
        except:
            pass
        return errors
```

### 6.3 엑셀 업로드 단계 (Explicit Wait + 오류 감지)

```python
# hometax_uploader.py — 업로드 단계 상세 (예외 처리 강화)

async def _step_upload(self, page, filepath):
    handler = HometaxExceptionHandler()

    # 1. 일괄등록 버튼 클릭
    btn = await page.wait_for_selector(
        'text=일괄등록, button:has-text("일괄"), a:has-text("일괄")',
        timeout=self.TIMEOUT_ELEMENT
    )
    await btn.click()
    await page.wait_for_timeout(2000)

    # 2. 팝업 오류 체크
    popup_errors = await handler.check_for_errors(page)
    if popup_errors:
        await handler.dismiss_popup(page)
        raise HometaxValidationError("일괄등록 팝업 열기 실패", popup_errors)

    # 3. 파일 선택 — Playwright file chooser 우선 시도
    try:
        async with page.expect_file_chooser(timeout=5000) as fc_info:
            await page.click('text=찾아보기, input[type="button"][value*="찾아"]')
        file_chooser = await fc_info.value
        await file_chooser.set_files(filepath)
    except Exception:
        # file chooser 실패 시 → pyautogui로 네이티브 대화상자 제어
        await page.click('text=찾아보기')
        await asyncio.sleep(2)
        import pyautogui
        pyautogui.typewrite(filepath.replace('/', '\\'), interval=0.02)
        pyautogui.press('enter')

    await page.wait_for_timeout(3000)

    # 4. 업로드 버튼 클릭 + 처리 대기
    upload_btn = await page.wait_for_selector(
        'text=업로드, button:has-text("업로드")',
        timeout=self.TIMEOUT_ELEMENT
    )
    await upload_btn.click()

    # ★ Explicit Wait: 네트워크 idle 또는 결과 테이블 출현까지 대기 ★
    try:
        await page.wait_for_load_state('networkidle', timeout=self.TIMEOUT_UPLOAD)
    except:
        pass  # networkidle 타임아웃은 무시하고 결과 확인으로 진행

    await page.wait_for_timeout(3000)  # 추가 렌더링 대기

    # 5. ★ 업로드 검증 오류 감지 (핵심) ★
    # 5-a. 팝업형 오류 (파일 형식 오류 등)
    popup_errors = await handler.check_for_errors(page)
    if popup_errors:
        screenshot = f"outputs/upload_error_{int(time.time())}.png"
        await page.screenshot(path=screenshot)
        await handler.dismiss_popup(page)
        raise HometaxValidationError("업로드 검증 오류", popup_errors)

    # 5-b. 테이블형 오류 (주민번호 오류, 금액 오류 등)
    table_errors = await handler.extract_upload_errors(page)
    if table_errors:
        screenshot = f"outputs/validation_error_{int(time.time())}.png"
        await page.screenshot(path=screenshot)
        raise HometaxValidationError(
            f"데이터 검증 오류 {len(table_errors)}건",
            [f"행 {e['line']}: {e['message']}" for e in table_errors]
        )

    # 6. 오류 없으면 적용
    apply_btn = await page.wait_for_selector(
        'text=적용, button:has-text("적용")',
        timeout=self.TIMEOUT_ELEMENT
    )
    await apply_btn.click()
    await page.wait_for_timeout(2000)

    return {"status": "success", "uploaded_file": filepath}
```

### 6.4 예외 클래스 정의

```python
class RPAError(Exception):
    """RPA 실행 중 복구 불가능한 오류"""
    def __init__(self, step: str, message: str):
        self.step = step
        super().__init__(f"[{step}] {message}")

class HometaxValidationError(RPAError):
    """홈택스가 반환한 데이터 검증 오류 (팝업/테이블)"""
    def __init__(self, message: str, errors: list):
        self.errors = errors
        super().__init__("VALIDATION", f"{message}: {errors}")

class RPAResult:
    """RPA 실행 결과 객체"""
    def __init__(self, period):
        self.period = period
        self.success = False
        self.error_step = None
        self.error_message = None
        self.validation_errors = []
        self.logs = []
        self.screenshots = []

    def log(self, step, status, message):
        self.logs.append({
            'step': step, 'status': status,
            'message': message, 'at': datetime.now().isoformat()
        })

    def save_to_file(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.__dict__, f, ensure_ascii=False, indent=2, default=str)
```

---

## 8. 배포 엣지 케이스 대응 (v3.1)

### 8.1 Playwright Chromium 자동 설치 (앱 최초 실행 시)

PyInstaller `.exe`에는 Playwright Chromium 바이너리가 포함되지 않음. 앱 시작 시 자동 감지+설치:

```python
# main.py — 앱 진입점

import subprocess
import sys
import os

def ensure_playwright_browser():
    """앱 최초 실행 시 Playwright Chromium 자동 설치"""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Chromium 실행 가능 여부 테스트 (즐시 닫음)
            browser = p.chromium.launch(headless=True)
            browser.close()
            return True
    except Exception:
        print("Chromium 브라우저가 설치되어 있지 않습니다. 자동 설치를 시작합니다...")
        try:
            subprocess.run(
                [sys.executable, '-m', 'playwright', 'install', 'chromium'],
                check=True,
                capture_output=True,
                text=True
            )
            print("Chromium 설치 완료")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Chromium 설치 실패: {e.stderr}")
            return False

def setup_security():
    """앱 최초 실행 시 .secret_key 자동 생성 (Edge Case #4)"""
    from core.crypto import CryptoManager
    crypto = CryptoManager()  # __init__에서 키 없으면 자동 생성
    return crypto

def main():
    from PySide6.QtWidgets import QApplication
    from gui.app import AutoTaxWindow, load_pretendard_fonts

    app = QApplication(sys.argv)
    load_pretendard_fonts(app)

    # ★ 최초 실행 초기화 ★
    setup_security()               # .secret_key 자동 생성
    ensure_playwright_browser()     # Chromium 자동 설치

    window = AutoTaxWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
```

### 8.2 다중 엑셀 파일 RPA 업로드 루프

1000건 초과 시 `excel_generator.py`가 파일을 분할하므로, RPA는 **여러 파일을 순차 업로드** 후 **제출은 1회만** 수행:

```python
# settlement_tab.py — RPA 실행 버튼 이벤트 (호출 예시)

def on_rpa_submit_clicked(self):
    """엑셀 생성 + RPA 실행 오케스트레이션"""
    period = self.current_period  # 예: '2026-03'

    # 1. 엑셀 생성 (단일 or 분할)
    files = self.excel_gen.generate_hometax_excel(period)  # list[dict]
    excel_paths = []
    for f in files:
        path = os.path.join('outputs', f['name'])
        save_workbook(f['workbook'], path)
        excel_paths.append(path)

    # 2. RPA 실행 (excel_paths 리스트 전달)
    auth_method = self.repo.get_setting('auth_method')['value']
    self.rpa_worker = RPAWorkerThread()
    self.rpa_worker.period = period
    self.rpa_worker.excel_paths = excel_paths  # ★ 리스트
    self.rpa_worker.auth_method = auth_method
    self.rpa_worker.start()
```

> `RPARunner.run()` 시그니처는 §6.1에서 `excel_paths: list[str]`로 수정됨  
> Step 3(Upload)에서 `for ep in excel_paths:` 루프로 순차 업로드, Step 4(Submit)은 루프 밖에서 1회만 실행

### 8.3 하이브리드 로그인 제어 아키텍처 (핸심)

> 기존 `pyautogui` 절대 좌표(x, y) 하드코딩 방식 → **전면 폐기**  
> 3단계 Fallback 체인: **Playwright DOM → pywinauto 창핸들 → pyautogui 이미지매칭**

```python
# hometax_login.py — 하이브리드 로그인 제어 (v3.1)

import asyncio
import time
import os

class HometaxLogin:
    """3단계 Fallback 로그인 제어 아키텍처"""

    async def login_with_certificate(self, page, cert_password: str):
        """
        공동인증서 로그인 — 3단계 Fallback:
        1) Playwright DOM Selector (웹 요소가 DOM에 존재할 때)
        2) pywinauto 창 핸들 제어 (AnySign4PC 같은 네이티브 팝업)
        3) pyautogui 이미지 템플릿 매칭 (최후의 보루)
        """

        # ── Step A: 홈택스 로그인 페이지 이동 ──
        await page.goto('https://hometax.go.kr')
        await page.click('text=로그인')
        await page.wait_for_timeout(2000)

        # ── Step B: [인증서 로그인] 탭 클릭 (Playwright DOM) ──
        cert_tab = await page.wait_for_selector(
            'text=인증서 로그인, a:has-text("인증서")',
            timeout=10000
        )
        await cert_tab.click()
        await page.wait_for_timeout(3000)  # AnySign 팝업 로딩 대기

        # ── Step C: 인증서 팝업 제어 (3단계 Fallback) ──
        cert_handled = await self._try_playwright_cert_popup(page, cert_password)
        if not cert_handled:
            cert_handled = await self._try_pywinauto_cert_popup(cert_password)
        if not cert_handled:
            cert_handled = await self._try_pyautogui_image_match(cert_password)
        if not cert_handled:
            raise Exception("인증서 팝업을 제어할 수 없습니다. 수동 로그인이 필요합니다.")

        # ── Step D: 로그인 성공 확인 ──
        try:
            await page.wait_for_selector('text=로그아웃', timeout=15000)
            return True
        except:
            await page.screenshot(path='outputs/login_failed.png')
            return False

    # ──────────────────────────────────────────────────────
    # Fallback Layer 1: Playwright DOM (웹 기반 인증서 UI)
    # ──────────────────────────────────────────────────────
    async def _try_playwright_cert_popup(self, page, password):
        """인증서 선택 UI가 웹 DOM 안에 있을 경우 (iframe/팝업)"""
        try:
            # 인증서 목록이 웹 DOM에 존재하는지 확인
            cert_list = await page.wait_for_selector(
                '#certList, .cert-list, [class*="cert"]',
                timeout=5000
            )
            if cert_list:
                # 첫 번째 인증서 선택
                first_cert = await page.query_selector(
                    '#certList tr:first-child, .cert-item:first-child')
                if first_cert:
                    await first_cert.click()
                # 비밀번호 입력
                pw_input = await page.wait_for_selector(
                    'input[type="password"], #certPwd', timeout=3000)
                await pw_input.fill(password)
                # 확인 버튼
                await page.click('button:has-text("확인"), input[value="확인"]')
                await page.wait_for_timeout(3000)
                return True
        except:
            pass
        return False

    # ──────────────────────────────────────────────────────
    # Fallback Layer 2: pywinauto 창 핸들 제어 (네이티브 팝업)
    # ──────────────────────────────────────────────────────
    async def _try_pywinauto_cert_popup(self, password):
        """AnySign4PC 등 네이티브 인증서 창 → pywinauto로 제어"""
        try:
            from pywinauto import Application, Desktop
            import time

            # 인증서 창 찾기 (제목에 '인증서' 또는 'AnySign' 포함)
            desktop = Desktop(backend='uia')
            cert_windows = desktop.windows(title_re='.*인증.*|.*AnySign.*|.*보안.*')

            if not cert_windows:
                return False

            cert_win = cert_windows[0]
            cert_win.set_focus()
            time.sleep(1)

            # 인증서 목록에서 첫 항목 선택
            try:
                tree = cert_win.child_window(control_type='Tree')
                items = tree.children()
                if items:
                    items[0].click_input()
                    time.sleep(0.5)
            except:
                # 트리가 없으면 리스트 시도
                try:
                    lst = cert_win.child_window(control_type='List')
                    lst.children()[0].click_input()
                except:
                    pass

            # 비밀번호 입력 (비밀번호 필드 찾기)
            pw_edit = cert_win.child_window(control_type='Edit')
            pw_edit.set_text(password)
            time.sleep(0.3)

            # 확인 버튼 클릭
            ok_btn = cert_win.child_window(title_re='.*확인.*|.*OK.*',
                                           control_type='Button')
            ok_btn.click_input()
            time.sleep(3)
            return True

        except Exception as e:
            print(f"pywinauto 실패: {e}")
            return False

    # ──────────────────────────────────────────────────────
    # Fallback Layer 3: pyautogui 이미지 템플릿 매칭 (최후의 보루)
    # ──────────────────────────────────────────────────────
    async def _try_pyautogui_image_match(self, password):
        """
        화면에 표시된 이미지를 기준으로 위치를 찾아 클릭.
        assets/images/ 폴더에 인증서 창 스크린샷 템플릿 저장 필요.
        절대 좌표 하드코딩 X — 이미지 매칭으로 위치 동적 탐지.
        """
        try:
            import pyautogui
            import time

            pyautogui.FAILSAFE = True
            template_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'images')

            # 1. 인증서 창의 비밀번호 입력 필드 이미지 찾기
            pw_field = pyautogui.locateCenterOnScreen(
                os.path.join(template_dir, 'cert_password_field.png'),
                confidence=0.8
            )
            if pw_field is None:
                return False

            pyautogui.click(pw_field)
            time.sleep(0.3)
            pyautogui.typewrite(password, interval=0.05)

            # 2. 확인 버튼 이미지 찾기 + 클릭
            ok_btn = pyautogui.locateCenterOnScreen(
                os.path.join(template_dir, 'cert_ok_button.png'),
                confidence=0.8
            )
            if ok_btn:
                pyautogui.click(ok_btn)
                time.sleep(3)
                return True

            return False

        except Exception as e:
            print(f"pyautogui 이미지매칭 실패: {e}")
            return False
```

**Fallback 체인 흐름도:**

```
인증서 로그인 버튼 클릭
       │
       ▼
┌──────────────────────────────────┐
│ Layer 1: Playwright DOM Selector   │  ← 웹 기반 인증서 UI
│  (#certList, input[type=password]) │    (성공 시 즉시 return)
└──────────┬───────────────────────┘
           │ 실패 시
           ▼
┌──────────────────────────────────┐
│ Layer 2: pywinauto 창 핸들 제어    │  ← AnySign 네이티브 팝업
│  (UIA backend, Tree/List/Edit)     │    (성공 시 즉시 return)
└──────────┬───────────────────────┘
           │ 실패 시
           ▼
┌──────────────────────────────────┐
│ Layer 3: pyautogui 이미지 매칭     │  ← 최후의 보루 (confidence=0.8)
│  (locateCenterOnScreen + 템플릿)  │    절대 좌표 하드코딩 전면 폐기
└──────────┬───────────────────────┘
           │ 전부 실패 시
           ▼
    Exception → "수동 로그인 필요" 안내
```

### 8.4 Secret Key 최초 자동 생성

> `crypto.py`의 `CryptoManager.__init__()`에서 이미 처리하고 있으나, 배포 시나리오를 위해 `main.py`에서도 명시적으로 `setup_security()`를 호출 (§8.1 참조)

```python
# core/crypto.py — __init__에서 키 자동 생성 (기존 코드 유지, 에러 처리 강화)

class CryptoManager:
    KEY_FILE = '.secret_key'

    def __init__(self, key_dir=None):
        """
        key_dir: .secret_key 파일을 저장할 디렉토리.
        PyInstaller .exe 배포 시 실행 파일과 같은 폴더에 생성.
        """
        if key_dir:
            self.key_path = os.path.join(key_dir, self.KEY_FILE)
        else:
            self.key_path = self.KEY_FILE

        self.fernet = Fernet(self._load_or_create_key())

    def _load_or_create_key(self) -> bytes:
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            print(f"암호화 키 최초 생성: {self.key_path}")
            key = Fernet.generate_key()
            # 파일 권한 제한 (Windows: 현재 사용자만 읽기 가능)
            os.makedirs(os.path.dirname(self.key_path) or '.', exist_ok=True)
            with open(self.key_path, 'wb') as f:
                f.write(key)
            return key

    def encrypt(self, plaintext: str) -> str:
        return self.fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.fernet.decrypt(ciphertext.encode()).decode()
```

---

## 7. 검증 계획

### 7.1 자동 테스트 (pytest)

```bash
# 실행 명령
cd AutoTax
python -m pytest tests/ -v
```

| 테스트 파일 | 검증 항목 |
|------------|----------|
| `test_tax_calculator.py` | 사업소득 3.3% 계산, 기타소득 8.8% 계산, 원단위 절사, 과세최저한 (125,000원 이하 → 0원) |
| `test_aggregator.py` | 동일 강사 2건 합산, 3건 합산, 다른 강사는 미합산 |
| `test_excel_generator.py` | **11컬럼 매핑 정확성**, **override된 final 값이 J/K열에 반영되는지**, 1000건 초과 파일 분할 |
| `test_validator.py` | 주민번호 13자리 검증, 하이픈 제거, 체크섬 |

### 7.2 수동 검증 (사용자)

1. 강사 3명 등록 → 강의 5건 입력(같은 강사 2건 포함) → [정산 실행] → 합산 확인
2. 정산 결과에서 1명의 소득세를 수동 수정 → [엑셀 다운로드] → 엑셀 J열에 수정값 반영 확인
3. 수동 수정 [되돌리기] → [엑셀 재다운로드] → 원래 자동계산 값 복원 확인
4. 생성된 엑셀 파일을 홈택스에 직접 업로드하여 검증 오류 0건 확인

---

## 9. 홈택스 공식 엑셀 양식 규격 (절대 변경 불가)

> 아래 양식은 홈택스가 정한 **간이지급명세서(사업소득) 엑셀 일괄등록** 공식 양식이다.
> 반드시 2행부터 데이터 입력, 최대 1,000라인. 1,000건 초과 시 파일 분할.

### 9.1 컬럼 정의 (A~K, 11컬럼)

| 컬럼 | 세식항목 | 데이터타입 | 항목설명 | 오류 기준 |
|------|----------|-----------|----------|----------|
| **A** | 일련번호 | 9(7) | 1부터 순차 부여 기재 | |
| **B** | 귀속연도 | X(4) | 소득자의 소득 귀속연도 | 날짜형식(YYYY)에 맞지 않으면 오류 |
| **C** | 귀속월 | X(2) | 소득자로부터 용역을 제공받은 월 기재 | 날짜형식(MM)에 맞지 않으면 오류 |
| **D** | 업종코드 | X(6) | 아래 업종 중 해당하는 업종의 코드를 기재 | 업종코드 이외의 코드를 기재한 경우 오류 |
| **E** | 소득자 성명(상호) | X(30) | 소득자의 성명(상호) 기재 | 기재 안 된 경우 오류 |
| **F** | 주민(사업자)등록번호 | X(13) | 소득자의 주민(사업자)등록번호 기재 | 기재 안 된 경우, 형식 불일치 오류 |
| **G** | 내외국인구분 | X(1) | 내국인: 1 / 외국인: 9 기재 | 1, 9가 아니면 오류 |
| **H** | 지급액 | 9(13) | 지급자가 지급한 지급액 | 지급액 < 0 이면 오류 |
| **I** | 세율 | 9(2) | 3%, 5%, 20% | 3, 5, 20이 아닌 오류. 940905→5% 필수, 940904·940905 제외 코드→3% 필수 |
| **J** | 소득세 | 9(13) | 지급자가 지급한 소득세액 | 소득세 < 0 이면 오류. 소득세 ≠ 지급액 × 세율이면 오류 |
| **K** | 지방소득세 | 9(13) | 지급자가 지급한 지방소득세액 | 지방소득세 < 0 이면 오류. 지방소득세 ≠ 소득세 × 10%이면 오류 |

### 9.2 세율 결정 규칙 (업종코드 기반)

| 업종코드 | 세율 | 비고 |
|---------|------|------|
| **940905** (봉사료수취자) | **5%** | 5%가 아니면 오류 |
| **940904** (직업운동가) | 별도 | 3%, 5%, 20% 가능 |
| **그 외 모든 코드** | **3%** | 3%가 아니면 오류 (복지관 강사 940903 포함) |

### 9.3 업종코드 전체 목록

| 코드 | 업종명 | | 코드 | 업종명 |
|------|--------|---|------|--------|
| 940100 | 저술가 | | 940913 | 대리운전 |
| 940200 | 화가관련 | | 940914 | 캐디 |
| 940301 | 작곡가 | | 940915 | 목욕관리사 |
| 940302 | 배우 | | 940916 | 행사도우미 |
| 940303 | 모델 | | 940917 | 심부름용역 |
| 940304 | 가수 | | 940918 | 퀵서비스 |
| 940305 | 성악가 | | 940919 | 물품배달 |
| 940306 | 1인미디어 콘텐츠창작자 | | 940920 | 학습지방문강사 |
| 940500 | 연예보조 | | 940921 | 교육교구방문강사 |
| 940600 | 자문·고문 | | 940922 | 대여제품방문점검원 |
| 940901 | 바둑기사 | | 940923 | 대출모집인 |
| **940903** | **학원강사** | | 940924 | 신용카드회원모집인 |
| 940904 | 직업운동가 | | 940925 | 방과후강사 |
| 940905 | 봉사료수취자 | | 940926 | 소프트웨어프리랜서 |
| 940906 | 보험설계 | | 940927 | 관광통역안내사 |
| 940907 | 음료배달 | | 940928 | 어린이통학버스기사 |
| 940908 | 방판·외판 | | 940929 | 중고자동차판매원 |
| 940909 | 기타자영업 | | 851101 | 병의원 |
| 940910 | 다단계판매 | | 940902 | 꽃꽂이교사 |
| 940911 | 기타모집수당 | | | |
| 940912 | 간병인 | | | |

> **복지관 기본 강사의 경우 `940909` (기타자영업) 사용으로 변경됨**

---

## 10. 홈택스 RPA(자동 제출) 기능의 범위와 한계

> **중요**: 현 단계(프로토타입 및 데스크톱 앱 V1)에서 지원하는 RPA(Robotic Process Automation) 작동 범위는 다음과 같습니다.

### 10.1 RPA 구현 범위
1. **자동 로그인**: 공동인증서(또는 간편인증) 정보를 활용하여 홈택스에 자동으로 로그인합니다.
2. **페이지 이동 및 양식 업로드**: 간이지급명세서(사업소득) 엑셀 일괄 등록 페이지로 자동으로 이동한 뒤, AutoTax 프로그램이 방금 전 단계에서 생성한 **`.xlsx` 파일을 홈택스에 자동 업로드(첨부)**하는 것까지만 수행합니다.

### 10.2 RPA 한계 (수동 처리 필요 영역)
1. **최종 제출 버튼 클릭**: 엑셀 파일이 업로드된 후, 홈택스 화면 내에서 오류 메시지가 없는지 시스템 검증을 통과하는 것을 눈으로 확인한 뒤, **화면 하단의 [최종 제출] 버튼은 강원도대치노인복지관 담당자가 직접 화면을 보고 마우스로 클릭**해야 합니다. (세금 체납/오류 신고 방지를 위한 안전 장치)
2. **접수증 다운로드**: 처리 결과 및 접수증(PDF) 수동 다운로드 보관

---

## 10. UI 핵심 원칙 (v4.0 추가)

### 10.1 모든 입력 항목에 수정 버튼 필수

> **원칙**: 데이터를 입력하는 **모든 화면**에는 반드시 **[수정]** 버튼이 존재해야 한다.
> 강사 정보, 프로그램 정보, 강의 내역, 정산 결과 등 예외 없음.

### 10.2 강사 등록 시 입력 항목

| 항목 | 필수 | 설명 |
|------|------|------|
| 강사명 |  | |
| 주민등록번호 |  | 13자리, Fernet 암호화 저장 |
| 업종코드 |  | 드롭다운 선택 (코드표 기반) |
| 프로그램 (1개 이상) |  | 과목구분(직접입력) + 프로그램명 + 회당 강사료 |
| 연락처 | ⬜ 선택 | |
| 이메일 | ⬜ 선택 | |
| 주소 | ⬜ 선택 | |
| 은행명/계좌번호 | ⬜ 선택 | |
| 내외국인 | ⬜ 선택 | 1(내국인) 또는 9(외국인), 기본값: 내국인 |
| 비고 | ⬜ 선택 | |

### 10.3 강사료 자동계산 흐름

```
[강사 선택] → [프로그램 선택] → [강의 횟수 입력]
       │              │                │
       ▼              ▼                ▼
  업종코드 확인    회당 강사료 확인    횟수 확인
                                      │
                                      ▼
                    총 강사료 = 회당 강사료 × 강의 횟수
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                  ▼
             소득세(3%)        지방소득세(0.3%)     실지급액
          = 총강사료 × 3%    = 소득세 × 10%     = 총강사료 - 소득세 - 지방소득세
          (원단위 절사)       (원단위 절사)
```

> **동일 강사 합산**: 같은 달에 여러 프로그램에서 강의한 경우, 주민번호 기준으로 합산 후 세액 계산

### 10.4 연간 신고자료 조회 및 합산 흐름

> **월별 선택 합산**: `연간 신고 데이터` 탭에서는 특정 1개 연도를 선택한 뒤, 하단의 **1월~12월 체크박스**를 통해 원하는 월만 조합하여 조회할 수 있습니다.
> **조회(선택 월 합산)** 버튼을 클릭하면, 선택된 월들에 발생한 지급액과 세액만 강사(주민번호)별로 합산되어 표시됩니다.

### 10.5 리스트 필터링 및 정렬 원칙 (v4.1 추가)

> **전역 검색 및 정렬**: 강사 관리, 강의 내역, 월별 정산, 연간 신고 등 데이터가 나열되는 가용 **모든 표(Table)** 상단이나 열 제목 요소에 **검색(필터링)과 정렬 기능**을 적용합니다. 강사명, 프로그램명, 과목구분 등 주요 데이터 컬럼을 오름차순/내림차순으로 정렬하고, 부분 일치 검색으로 빠르게 데이터를 찾을 수 있게 지원해야 합니다.
> **강의 내역 특화 양식 출력**: 강의 내역 탭 상단에는 현재 선택된 조회 연월을 기준으로 데이터를 가져오는 **[조회] 버튼**이 존재해야 하며, 표출된 내역을 과목구분 등으로 필터링 한 뒤 **[양식 출력]** 버튼을 통해 내부 기안용 맞춤형 엑셀(연번, 프로그램, 강사, 1회강사료, 횟수, 강사료, 소득세, 주민세, 합계, 실지급액, 계좌번호)을 즉시 다운로드 할 수 있어야 합니다.
