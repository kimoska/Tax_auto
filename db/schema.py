"""
AutoTax — 데이터베이스 스키마 정의 및 초기화
plan.md §3.1 기반
"""
from db.connection import DatabaseConnection


# ─────────────────────────────────────────────
# DDL 정의 (plan.md §3.1 그대로 구현)
# ─────────────────────────────────────────────

TABLES_DDL = [
    # ① 강사 마스터
    """
    CREATE TABLE IF NOT EXISTS instructors (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    NOT NULL,
        resident_id     TEXT    NOT NULL,
        phone           TEXT,
        email           TEXT,
        address         TEXT,
        industry_code   TEXT    NOT NULL DEFAULT '940909',
        is_foreigner    TEXT    NOT NULL DEFAULT '1',
        bank_name       TEXT,
        account_number  TEXT,
        memo            TEXT,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,

    # ①-2 강사별 프로그램 (1강사 N프로그램)
    """
    CREATE TABLE IF NOT EXISTS instructor_programs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        instructor_id   INTEGER NOT NULL REFERENCES instructors(id) ON DELETE CASCADE,
        category        TEXT    NOT NULL,
        program_name    TEXT    NOT NULL,
        department      TEXT,
        fee_per_session INTEGER NOT NULL DEFAULT 0,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,

    # ② 월별 강의/지급 내역
    """
    CREATE TABLE IF NOT EXISTS lectures (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        instructor_id   INTEGER NOT NULL REFERENCES instructors(id),
        program_id      INTEGER NOT NULL REFERENCES instructor_programs(id),
        period          TEXT    NOT NULL,
        payment_month   TEXT    NOT NULL,
        session_count   INTEGER NOT NULL DEFAULT 0,
        fee_per_session INTEGER NOT NULL DEFAULT 0,
        payment_amount  INTEGER NOT NULL DEFAULT 0,
        status          TEXT    NOT NULL DEFAULT '입력완료'
                        CHECK(status IN ('입력완료','정산완료','제출완료')),
        created_by      TEXT,
        created_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at      TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,

    # ③ 정산 결과
    """
    CREATE TABLE IF NOT EXISTS settlements (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        instructor_id   INTEGER NOT NULL REFERENCES instructors(id),
        period          TEXT    NOT NULL,
        industry_code   TEXT    NOT NULL,
        is_foreigner    TEXT    NOT NULL DEFAULT '1',
        total_payment   INTEGER NOT NULL,
        tax_rate        INTEGER NOT NULL DEFAULT 3,

        calc_income_tax INTEGER NOT NULL,
        calc_local_tax  INTEGER NOT NULL,
        calc_net_payment INTEGER NOT NULL,

        ovr_income_tax  INTEGER DEFAULT NULL,
        ovr_local_tax   INTEGER DEFAULT NULL,
        ovr_reason      TEXT    DEFAULT NULL,
        ovr_at          TEXT    DEFAULT NULL,
        ovr_by          TEXT    DEFAULT NULL,

        final_income_tax INTEGER NOT NULL,
        final_local_tax  INTEGER NOT NULL,
        final_net_payment INTEGER NOT NULL,

        is_submitted    INTEGER NOT NULL DEFAULT 0,
        submitted_at    TEXT    DEFAULT NULL,
        excel_filename  TEXT    DEFAULT NULL,
        receipt_path    TEXT    DEFAULT NULL,

        created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime')),

        UNIQUE(instructor_id, period)
    )
    """,

    # ④ 감사 로그
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        action          TEXT    NOT NULL,
        target_table    TEXT    NOT NULL,
        target_id       INTEGER,
        period          TEXT,
        before_json     TEXT,
        after_json      TEXT,
        reason          TEXT,
        performed_by    TEXT,
        performed_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,

    # ⑤ 환경설정 (Key-Value)
    """
    CREATE TABLE IF NOT EXISTS app_settings (
        key             TEXT PRIMARY KEY,
        value           TEXT NOT NULL,
        is_encrypted    INTEGER NOT NULL DEFAULT 0,
        category        TEXT NOT NULL DEFAULT 'general',
        updated_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
    )
    """,
]

# 인덱스 정의
INDEXES_DDL = [
    "CREATE INDEX IF NOT EXISTS idx_programs_instructor ON instructor_programs(instructor_id)",
    "CREATE INDEX IF NOT EXISTS idx_lectures_period ON lectures(period)",
    "CREATE INDEX IF NOT EXISTS idx_lectures_instructor ON lectures(instructor_id, period)",
    "CREATE INDEX IF NOT EXISTS idx_lectures_program ON lectures(program_id)",
    "CREATE INDEX IF NOT EXISTS idx_settlements_period ON settlements(period)",
    "CREATE INDEX IF NOT EXISTS idx_settlements_instructor ON settlements(instructor_id, period)",
    "CREATE INDEX IF NOT EXISTS idx_audit_period ON audit_logs(period)",
]

# 초기 설정 데이터
INITIAL_SETTINGS = [
    ('org_name',              '',             0, 'organization'),
    ('org_biz_number',        '',             0, 'organization'),
    ('org_representative',    '',             0, 'organization'),
    ('org_address',           '',             0, 'organization'),
    ('org_tax_office',        '',             0, 'organization'),
    ('auth_method',           'certificate',  0, 'auth'),
    ('cert_password',         '',             1, 'auth'),
    ('cert_path',             '',             0, 'auth'),
    ('simple_auth_id',        '',             0, 'auth'),
    ('default_industry_code', '940909',       0, 'defaults'),
]


def initialize_database(db: DatabaseConnection = None):
    """데이터베이스 초기화: 테이블 생성 + 인덱스 + 초기 데이터"""
    if db is None:
        db = DatabaseConnection()

    conn = db.get_connection()

    # 테이블 생성
    for ddl in TABLES_DDL:
        conn.execute(ddl)

    # 인덱스 생성
    for idx_ddl in INDEXES_DDL:
        conn.execute(idx_ddl)

    # 초기 설정 데이터 삽입
    conn.executemany(
        """INSERT OR IGNORE INTO app_settings (key, value, is_encrypted, category)
           VALUES (?, ?, ?, ?)""",
        INITIAL_SETTINGS
    )

    conn.commit()
    print("✅ 데이터베이스 초기화 완료")
