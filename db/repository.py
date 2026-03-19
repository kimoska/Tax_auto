"""
AutoTax — 전 테이블 CRUD 리포지토리
plan.md §4.2 기반 (COALESCE 로직 포함)
"""
import json
from db.connection import DatabaseConnection


class Repository:
    """전 테이블 CRUD 함수 모음"""

    def __init__(self, db: DatabaseConnection = None):
        self.db = db or DatabaseConnection()

    # ═══════════════════════════════════════════
    # 강사 (instructors)
    # ═══════════════════════════════════════════

    def get_all_instructors(self) -> list[dict]:
        """전체 강사 목록 조회"""
        return self.db.fetchall(
            "SELECT * FROM instructors ORDER BY name"
        )

    def get_instructor(self, instructor_id: int) -> dict | None:
        """강사 단건 조회"""
        return self.db.fetchone(
            "SELECT * FROM instructors WHERE id = ?", (instructor_id,)
        )

    def create_instructor(self, data: dict) -> int:
        """강사 등록 → 생성된 ID 반환"""
        cursor = self.db.execute(
            """INSERT INTO instructors
               (name, resident_id, phone, email, address,
                industry_code, is_foreigner, bank_name, account_number, memo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (data['name'], data['resident_id'],
             data.get('phone', ''), data.get('email', ''),
             data.get('address', ''), data.get('industry_code', '940909'),
             data.get('is_foreigner', '1'),
             data.get('bank_name', ''), data.get('account_number', ''),
             data.get('memo', ''))
        )
        return cursor.lastrowid

    def update_instructor(self, instructor_id: int, data: dict):
        """강사 정보 수정"""
        self.db.execute(
            """UPDATE instructors SET
               name=?, resident_id=?, phone=?, email=?, address=?,
               industry_code=?, is_foreigner=?, bank_name=?, account_number=?,
               memo=?, updated_at=datetime('now','localtime')
               WHERE id=?""",
            (data['name'], data['resident_id'],
             data.get('phone', ''), data.get('email', ''),
             data.get('address', ''), data.get('industry_code', '940909'),
             data.get('is_foreigner', '1'),
             data.get('bank_name', ''), data.get('account_number', ''),
             data.get('memo', ''), instructor_id)
        )

    def delete_instructor(self, instructor_id: int):
        """강사 삭제 (CASCADE로 프로그램도 삭제)"""
        self.db.execute("DELETE FROM instructors WHERE id=?", (instructor_id,))

    # ═══════════════════════════════════════════
    # 프로그램 (instructor_programs)
    # ═══════════════════════════════════════════

    def get_programs_by_instructor(self, instructor_id: int) -> list[dict]:
        """특정 강사의 프로그램 목록"""
        return self.db.fetchall(
            "SELECT * FROM instructor_programs WHERE instructor_id=? ORDER BY id",
            (instructor_id,)
        )

    def get_program(self, program_id: int) -> dict | None:
        """프로그램 단건 조회"""
        return self.db.fetchone(
            "SELECT * FROM instructor_programs WHERE id=?", (program_id,)
        )

    def create_program(self, data: dict) -> int:
        """프로그램 등록"""
        cursor = self.db.execute(
            """INSERT INTO instructor_programs
               (instructor_id, category, program_name, department, fee_per_session)
               VALUES (?, ?, ?, ?, ?)""",
            (data['instructor_id'], data['category'], data['program_name'],
             data.get('department', ''), data.get('fee_per_session', 0))
        )
        return cursor.lastrowid

    def update_program(self, program_id: int, data: dict):
        """프로그램 수정"""
        self.db.execute(
            """UPDATE instructor_programs SET
               category=?, program_name=?, department=?, fee_per_session=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (data['category'], data['program_name'],
             data.get('department', ''), data.get('fee_per_session', 0),
             program_id)
        )

    def delete_program(self, program_id: int):
        """프로그램 삭제"""
        self.db.execute("DELETE FROM instructor_programs WHERE id=?", (program_id,))

    def delete_programs_by_instructor(self, instructor_id: int):
        """특정 강사의 모든 프로그램 삭제"""
        self.db.execute(
            "DELETE FROM instructor_programs WHERE instructor_id=?",
            (instructor_id,)
        )

    # ═══════════════════════════════════════════
    # 강의 (lectures)
    # ═══════════════════════════════════════════

    def get_lectures_by_period(self, period: str) -> list[dict]:
        """특정 기간의 강의 목록 (강사/프로그램 정보 JOIN)"""
        return self.db.fetchall(
            """SELECT l.*,
                      i.name AS instructor_name,
                      i.industry_code,
                      i.is_foreigner,
                      i.resident_id,
                      i.bank_name,
                      i.account_number,
                      p.category AS program_category,
                      p.program_name
               FROM lectures l
               JOIN instructors i ON l.instructor_id = i.id
               JOIN instructor_programs p ON l.program_id = p.id
               WHERE l.period = ?
               ORDER BY i.name, p.program_name""",
            (period,)
        )

    def get_lecture(self, lecture_id: int) -> dict | None:
        """강의 단건 조회"""
        return self.db.fetchone("SELECT * FROM lectures WHERE id=?", (lecture_id,))

    def create_lecture(self, data: dict) -> int:
        """강의 내역 등록"""
        payment = data['session_count'] * data['fee_per_session']
        cursor = self.db.execute(
            """INSERT INTO lectures
               (instructor_id, program_id, period, payment_month,
                session_count, fee_per_session, payment_amount)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (data['instructor_id'], data['program_id'],
             data['period'], data.get('payment_month', data['period']),
             data['session_count'], data['fee_per_session'], payment)
        )
        return cursor.lastrowid

    def update_lecture(self, lecture_id: int, data: dict):
        """강의 내역 수정"""
        payment = data['session_count'] * data['fee_per_session']
        self.db.execute(
            """UPDATE lectures SET
               instructor_id=?, program_id=?, period=?, payment_month=?,
               session_count=?, fee_per_session=?, payment_amount=?,
               updated_at=datetime('now','localtime')
               WHERE id=?""",
            (data['instructor_id'], data['program_id'],
             data['period'], data.get('payment_month', data['period']),
             data['session_count'], data['fee_per_session'], payment,
             lecture_id)
        )

    def delete_lecture(self, lecture_id: int):
        """강의 내역 삭제"""
        self.db.execute("DELETE FROM lectures WHERE id=?", (lecture_id,))

    # ═══════════════════════════════════════════
    # 정산 (settlements) — plan.md §4.2 COALESCE 로직
    # ═══════════════════════════════════════════

    def get_settlements_by_period(self, period: str) -> list[dict]:
        """특정 기간 정산 목록 (강사 정보 JOIN)"""
        return self.db.fetchall(
            """SELECT s.*, i.name, i.resident_id
               FROM settlements s
               JOIN instructors i ON s.instructor_id = i.id
               WHERE s.period = ?
               ORDER BY i.name""",
            (period,)
        )

    def get_settlement(self, settlement_id: int) -> dict | None:
        """정산 단건 조회"""
        return self.db.fetchone("SELECT * FROM settlements WHERE id=?", (settlement_id,))

    def upsert_settlement(self, instructor_id: int, period: str,
                          calc_data: dict, override: dict = None):
        """
        정산 결과 저장/갱신.
        final 값은 override 있으면 override, 없으면 calc 사용.
        (plan.md §4.2 핵심 로직)
        """
        ovr_income = override.get('income_tax') if override else None
        ovr_local = override.get('local_tax') if override else None
        ovr_reason = override.get('reason') if override else None
        ovr_by = override.get('by') if override else None

        final_income = ovr_income if ovr_income is not None else calc_data['income_tax']
        final_local = ovr_local if ovr_local is not None else calc_data['local_tax']
        final_net = calc_data['total_payment'] - final_income - final_local

        self.db.execute(
            """INSERT INTO settlements (
                instructor_id, period, industry_code, is_foreigner,
                total_payment, tax_rate,
                calc_income_tax, calc_local_tax, calc_net_payment,
                ovr_income_tax, ovr_local_tax, ovr_reason, ovr_at, ovr_by,
                final_income_tax, final_local_tax, final_net_payment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'), ?, ?, ?, ?)
            ON CONFLICT(instructor_id, period) DO UPDATE SET
                total_payment    = excluded.total_payment,
                industry_code    = excluded.industry_code,
                is_foreigner     = excluded.is_foreigner,
                tax_rate         = excluded.tax_rate,
                calc_income_tax  = excluded.calc_income_tax,
                calc_local_tax   = excluded.calc_local_tax,
                calc_net_payment = excluded.calc_net_payment,
                -- 재정산 시에도 기존 override 보존
                ovr_income_tax   = COALESCE(settlements.ovr_income_tax, excluded.ovr_income_tax),
                ovr_local_tax    = COALESCE(settlements.ovr_local_tax, excluded.ovr_local_tax),
                -- final은 항상 재계산
                final_income_tax = COALESCE(settlements.ovr_income_tax, excluded.calc_income_tax),
                final_local_tax  = COALESCE(settlements.ovr_local_tax, excluded.calc_local_tax),
                final_net_payment = excluded.total_payment
                    - COALESCE(settlements.ovr_income_tax, excluded.calc_income_tax)
                    - COALESCE(settlements.ovr_local_tax, excluded.calc_local_tax),
                updated_at = datetime('now','localtime')
            """,
            (instructor_id, period,
             calc_data['industry_code'], calc_data['is_foreigner'],
             calc_data['total_payment'], calc_data['tax_rate'],
             calc_data['income_tax'], calc_data['local_tax'], calc_data['net_payment'],
             ovr_income, ovr_local, ovr_reason, ovr_by,
             final_income, final_local, final_net)
        )

    def apply_override(self, settlement_id: int,
                       income_tax: int, local_tax: int,
                       reason: str, user: str = ''):
        """수동 수정 적용 — final 값 즉시 갱신 (plan.md §4.2)"""
        settlement = self.get_settlement(settlement_id)
        if not settlement:
            raise ValueError(f"정산 ID {settlement_id} 없음")

        # 감사 로그 기록
        self._log_audit(
            'OVERRIDE', 'settlements', settlement_id,
            settlement.get('period'),
            before={'income_tax': settlement['final_income_tax'],
                    'local_tax': settlement['final_local_tax']},
            after={'income_tax': income_tax, 'local_tax': local_tax},
            reason=reason, user=user
        )

        net = settlement['total_payment'] - income_tax - local_tax
        self.db.execute(
            """UPDATE settlements SET
                ovr_income_tax   = ?,
                ovr_local_tax    = ?,
                ovr_reason       = ?,
                ovr_at           = datetime('now','localtime'),
                ovr_by           = ?,
                final_income_tax = ?,
                final_local_tax  = ?,
                final_net_payment = ?,
                updated_at       = datetime('now','localtime')
            WHERE id = ?""",
            (income_tax, local_tax, reason, user,
             income_tax, local_tax, net,
             settlement_id)
        )

    def revert_override(self, settlement_id: int):
        """수동 수정 되돌리기 — final을 calc로 복원 (plan.md §4.2)"""
        settlement = self.get_settlement(settlement_id)
        if not settlement:
            raise ValueError(f"정산 ID {settlement_id} 없음")

        self._log_audit(
            'REVERT', 'settlements', settlement_id,
            settlement.get('period'),
            before={'ovr_income_tax': settlement.get('ovr_income_tax'),
                    'ovr_local_tax': settlement.get('ovr_local_tax')},
            after={'ovr_income_tax': None, 'ovr_local_tax': None},
            reason='Override 되돌리기'
        )

        self.db.execute(
            """UPDATE settlements SET
                ovr_income_tax   = NULL,
                ovr_local_tax    = NULL,
                ovr_reason       = NULL,
                ovr_at           = NULL,
                ovr_by           = NULL,
                final_income_tax = calc_income_tax,
                final_local_tax  = calc_local_tax,
                final_net_payment = total_payment - calc_income_tax - calc_local_tax,
                updated_at       = datetime('now','localtime')
            WHERE id = ?""",
            (settlement_id,)
        )

    # ═══════════════════════════════════════════
    # 환경설정 (app_settings)
    # ═══════════════════════════════════════════

    def get_setting(self, key: str) -> dict | None:
        """설정값 조회"""
        return self.db.fetchone(
            "SELECT * FROM app_settings WHERE key=?", (key,)
        )

    def get_settings_by_category(self, category: str) -> list[dict]:
        """카테고리별 설정 목록"""
        return self.db.fetchall(
            "SELECT * FROM app_settings WHERE category=?", (category,)
        )

    def update_setting(self, key: str, value: str, is_encrypted: int = 0):
        """설정값 갱신"""
        self.db.execute(
            """UPDATE app_settings SET
               value=?, is_encrypted=?, updated_at=datetime('now','localtime')
               WHERE key=?""",
            (value, is_encrypted, key)
        )

    # ═══════════════════════════════════════════
    # 감사 로그 (audit_logs) — 내부용
    # ═══════════════════════════════════════════

    def _log_audit(self, action: str, table: str, target_id: int,
                   period: str = None, before: dict = None,
                   after: dict = None, reason: str = None, user: str = ''):
        """감사 로그 기록"""
        self.db.execute(
            """INSERT INTO audit_logs
               (action, target_table, target_id, period,
                before_json, after_json, reason, performed_by)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (action, table, target_id, period,
             json.dumps(before, ensure_ascii=False) if before else None,
             json.dumps(after, ensure_ascii=False) if after else None,
             reason, user)
        )

    def get_audit_logs(self, period: str = None, limit: int = 50) -> list[dict]:
        """감사 로그 조회"""
        if period:
            return self.db.fetchall(
                "SELECT * FROM audit_logs WHERE period=? ORDER BY performed_at DESC LIMIT ?",
                (period, limit)
            )
        return self.db.fetchall(
            "SELECT * FROM audit_logs ORDER BY performed_at DESC LIMIT ?",
            (limit,)
        )

    # ═══════════════════════════════════════════
    # 연간 데이터 조회 (집계 쿼리)
    # ═══════════════════════════════════════════

    def get_annual_summary(self, year: str, months: list[str] = None) -> list[dict]:
        """
        연간 합산 데이터 조회 (plan.md §3.2).
        months가 지정되면 해당 월만 합산.
        """
        if months:
            placeholders = ','.join(['?' for _ in months])
            periods = [f"{year}-{m}" for m in months]
            return self.db.fetchall(
                f"""SELECT
                        s.instructor_id,
                        i.name,
                        i.resident_id,
                        s.industry_code,
                        SUM(s.total_payment)      AS annual_total,
                        SUM(s.final_income_tax)   AS annual_income_tax,
                        SUM(s.final_local_tax)    AS annual_local_tax,
                        SUM(s.final_net_payment)  AS annual_net_payment
                    FROM settlements s
                    JOIN instructors i ON s.instructor_id = i.id
                    WHERE s.period IN ({placeholders})
                    GROUP BY s.instructor_id
                    ORDER BY i.name""",
                tuple(periods)
            )
        else:
            return self.db.fetchall(
                """SELECT
                        s.instructor_id,
                        i.name,
                        i.resident_id,
                        s.industry_code,
                        SUM(s.total_payment)      AS annual_total,
                        SUM(s.final_income_tax)   AS annual_income_tax,
                        SUM(s.final_local_tax)    AS annual_local_tax,
                        SUM(s.final_net_payment)  AS annual_net_payment
                    FROM settlements s
                    JOIN instructors i ON s.instructor_id = i.id
                    WHERE s.period BETWEEN ? AND ?
                    GROUP BY s.instructor_id
                    ORDER BY i.name""",
                (f"{year}-01", f"{year}-12")
            )
