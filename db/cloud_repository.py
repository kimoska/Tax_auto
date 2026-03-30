"""
AutoTax — Firestore 클라우드 리포지토리
기존 `Repository` 클래스와 동일한 인터페이스를 유지하면서
Firestore REST API를 통해 CRUD 수행
"""
import json
from datetime import datetime, timezone
from core.firestore_client import FirestoreClient


import time

class CloudRepository:
    """Firestore 기반 전 테이블 CRUD 함수 모음"""

    def __init__(self, auth):
        """
        Args:
            auth: FirebaseAuth 인스턴스 (인증 정보 + org_id 포함)
        """
        self.auth = auth
        self.client = FirestoreClient(auth)
        self.org_id = auth.org_id
        self._cache = {}

    def _invalidate_cache(self, key: str):
        if key in self._cache:
            del self._cache[key]

    def _org(self, sub_path: str = '') -> str:
        """기관 문서 경로 생성"""
        base = f"organizations/{self.org_id}"
        return f"{base}/{sub_path}" if sub_path else base

    def _now_iso(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ═══════════════════════════════════════════
    # 강사 (instructors)
    # ═══════════════════════════════════════════

    def get_all_instructors(self) -> list[dict]:
        """전체 강사 목록 조회 (5초 캐싱)"""
        now = time.time()
        cached = self._cache.get('instructors')
        if cached and now - cached['time'] < 5.0:
            return cached['data']
            
        docs = self.client.list_documents(self._org('instructors'))
        result = sorted(docs, key=lambda x: x.get('name', ''))
        self._cache['instructors'] = {'time': now, 'data': result}
        return result

    def get_instructor(self, instructor_id) -> dict | None:
        """강사 단건 조회"""
        return self.client.get_document(self._org(f'instructors/{instructor_id}'))

    def create_instructor(self, data: dict) -> str:
        """강사 등록 → 생성된 ID 반환"""
        self._invalidate_cache('instructors')
        doc_data = {
            'name': data['name'],
            'resident_id': data['resident_id'],
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'address': data.get('address', ''),
            'industry_code': data.get('industry_code', '940909'),
            'is_foreigner': data.get('is_foreigner', '1'),
            'bank_name': data.get('bank_name', ''),
            'account_number': data.get('account_number', ''),
            'memo': data.get('memo', ''),
            'created_at': self._now_iso(),
            'updated_at': self._now_iso()
        }
        result = self.client.create_document(self._org('instructors'), doc_data)
        return result['id']

    def update_instructor(self, instructor_id, data: dict):
        """강사 정보 수정"""
        self._invalidate_cache('instructors')
        doc_data = {
            'name': data['name'],
            'resident_id': data['resident_id'],
            'phone': data.get('phone', ''),
            'email': data.get('email', ''),
            'address': data.get('address', ''),
            'industry_code': data.get('industry_code', '940909'),
            'is_foreigner': data.get('is_foreigner', '1'),
            'bank_name': data.get('bank_name', ''),
            'account_number': data.get('account_number', ''),
            'memo': data.get('memo', ''),
            'updated_at': self._now_iso()
        }
        self.client.update_document(self._org(f'instructors/{instructor_id}'), doc_data)

    def delete_instructor(self, instructor_id):
        """강사 삭제 (연관 프로그램도 삭제)"""
        self._invalidate_cache('instructors')
        self._invalidate_cache('programs')
        # 연관 프로그램 삭제
        programs = self.get_programs_by_instructor(instructor_id)
        for prog in programs:
            self.client.delete_document(self._org(f'instructor_programs/{prog["id"]}'))
        # 강사 삭제
        self.client.delete_document(self._org(f'instructors/{instructor_id}'))

    # ═══════════════════════════════════════════
    # 프로그램 (instructor_programs)
    # ═══════════════════════════════════════════

    def get_programs_by_instructor(self, instructor_id) -> list[dict]:
        """특정 강사의 프로그램 목록"""
        docs = self.client.list_documents(
            self._org('instructor_programs'),
            filters=[('instructor_id', 'EQUAL', str(instructor_id))]
        )
        return docs

    def get_all_programs(self) -> list[dict]:
        """모든 프로그램 목록 (UI 성능 최적화용 - 5초 캐싱)"""
        now = time.time()
        cached = self._cache.get('programs')
        if cached and now - cached['time'] < 5.0:
            return cached['data']
            
        docs = self.client.list_documents(self._org('instructor_programs'))
        self._cache['programs'] = {'time': now, 'data': docs}
        return docs

    def get_program(self, program_id) -> dict | None:
        """프로그램 단건 조회"""
        return self.client.get_document(self._org(f'instructor_programs/{program_id}'))

    def create_program(self, data: dict) -> str:
        """프로그램 등록"""
        self._invalidate_cache('programs')
        doc_data = {
            'instructor_id': str(data['instructor_id']),
            'category': data['category'],
            'program_name': data['program_name'],
            'department': data.get('department', ''),
            'fee_per_session': data.get('fee_per_session', 0),
            'created_at': self._now_iso(),
            'updated_at': self._now_iso()
        }
        result = self.client.create_document(
            self._org('instructor_programs'), doc_data
        )
        return result['id']

    def update_program(self, program_id, data: dict):
        """프로그램 수정"""
        self._invalidate_cache('programs')
        doc_data = {
            'category': data['category'],
            'program_name': data['program_name'],
            'department': data.get('department', ''),
            'fee_per_session': data.get('fee_per_session', 0),
            'updated_at': self._now_iso()
        }
        self.client.update_document(
            self._org(f'instructor_programs/{program_id}'), doc_data
        )

    def delete_program(self, program_id):
        """프로그램 삭제"""
        self._invalidate_cache('programs')
        self.client.delete_document(self._org(f'instructor_programs/{program_id}'))

    def delete_programs_by_instructor(self, instructor_id):
        """특정 강사의 모든 프로그램 삭제"""
        self._invalidate_cache('programs')
        programs = self.get_programs_by_instructor(instructor_id)
        for prog in programs:
            self.client.delete_document(self._org(f'instructor_programs/{prog["id"]}'))

    # ═══════════════════════════════════════════
    # 강의 (lectures)
    # ═══════════════════════════════════════════

    def get_lectures_by_period(self, period: str) -> list[dict]:
        """
        특정 기간의 강의 목록 (강사/프로그램 정보 병합).
        SQLite의 JOIN 쿼리를 여러 조회 + 파이썬 병합으로 대체.
        """
        lectures = self.client.list_documents(
            self._org('lectures'),
            filters=[('period', 'EQUAL', period)]
        )

        if not lectures:
            return []

        # 강사 및 프로그램 정보를 캐시
        instructors_map = {}
        programs_map = {}

        all_instructors = self.get_all_instructors()
        for inst in all_instructors:
            instructors_map[inst['id']] = inst

        all_programs = self.client.list_documents(self._org('instructor_programs'))
        for prog in all_programs:
            programs_map[prog['id']] = prog

        # 병합
        result = []
        for lec in lectures:
            inst_id = lec.get('instructor_id', '')
            prog_id = lec.get('program_id', '')
            inst = instructors_map.get(inst_id, {})
            prog = programs_map.get(prog_id, {})

            merged = {**lec}
            merged['instructor_name'] = inst.get('name', '')
            merged['industry_code'] = inst.get('industry_code', '940909')
            merged['is_foreigner'] = inst.get('is_foreigner', '1')
            merged['resident_id'] = inst.get('resident_id', '')
            merged['bank_name'] = inst.get('bank_name', '')
            merged['account_number'] = inst.get('account_number', '')
            merged['program_category'] = prog.get('category', '')
            merged['program_name'] = prog.get('program_name', '')
            result.append(merged)

        return sorted(result, key=lambda x: (x.get('instructor_name', ''), x.get('program_name', '')))

    def get_lecture(self, lecture_id) -> dict | None:
        """강의 단건 조회"""
        return self.client.get_document(self._org(f'lectures/{lecture_id}'))

    def create_lecture(self, data: dict) -> str:
        """강의 내역 등록"""
        payment = data['session_count'] * data['fee_per_session']
        doc_data = {
            'instructor_id': str(data['instructor_id']),
            'program_id': str(data['program_id']),
            'period': data['period'],
            'payment_month': data.get('payment_month', data['period']),
            'session_count': data['session_count'],
            'fee_per_session': data['fee_per_session'],
            'payment_amount': payment,
            'status': '입력완료',
            'created_by': self.auth.email or '',
            'created_at': self._now_iso(),
            'updated_at': self._now_iso()
        }
        result = self.client.create_document(self._org('lectures'), doc_data)
        return result['id']

    def update_lecture(self, lecture_id, data: dict):
        """강의 내역 수정"""
        payment = data['session_count'] * data['fee_per_session']
        doc_data = {
            'instructor_id': str(data['instructor_id']),
            'program_id': str(data['program_id']),
            'period': data['period'],
            'payment_month': data.get('payment_month', data['period']),
            'session_count': data['session_count'],
            'fee_per_session': data['fee_per_session'],
            'payment_amount': payment,
            'updated_at': self._now_iso()
        }
        self.client.update_document(self._org(f'lectures/{lecture_id}'), doc_data)

    def delete_lecture(self, lecture_id):
        """강의 내역 삭제"""
        self.client.delete_document(self._org(f'lectures/{lecture_id}'))

    # ═══════════════════════════════════════════
    # 정산 (settlements) — COALESCE 로직 유지
    # ═══════════════════════════════════════════

    def get_settlements_by_period(self, period: str) -> list[dict]:
        """특정 기간 정산 목록 (강사 정보 병합)"""
        settlements = self.client.list_documents(
            self._org('settlements'),
            filters=[('period', 'EQUAL', period)]
        )

        if not settlements:
            return []

        # 강사 정보 병합
        instructors_map = {}
        all_instructors = self.get_all_instructors()
        for inst in all_instructors:
            instructors_map[inst['id']] = inst

        result = []
        for stl in settlements:
            inst_id = stl.get('instructor_id', '')
            inst = instructors_map.get(inst_id, {})
            merged = {**stl}
            merged['name'] = inst.get('name', '')
            merged['resident_id'] = inst.get('resident_id', '')
            result.append(merged)

        return sorted(result, key=lambda x: x.get('name', ''))

    def get_settlement(self, settlement_id) -> dict | None:
        """정산 단건 조회"""
        return self.client.get_document(self._org(f'settlements/{settlement_id}'))

    def delete_settlements_by_period(self, period: str):
        """특정 기간의 모든 정산 문서 삭제"""
        settlements = self.client.list_documents(
            self._org('settlements'),
            filters=[('period', 'EQUAL', period)]
        )
        for stl in settlements:
            self.client.delete_document(self._org(f'settlements/{stl["id"]}'))

    def _find_settlement_by_instructor_period(self, instructor_id, period: str) -> dict | None:
        """강사+기간으로 기존 정산 문서 찾기"""
        docs = self.client.list_documents(
            self._org('settlements'),
            filters=[
                ('instructor_id', 'EQUAL', str(instructor_id)),
                ('period', 'EQUAL', period)
            ]
        )
        return docs[0] if docs else None

    def upsert_settlement(self, instructor_id, period: str,
                          calc_data: dict, override: dict = None):
        """
        정산 결과 저장/갱신.
        final 값은 override 있으면 override, 없으면 calc 사용.
        """
        ovr_income = override.get('income_tax') if override else None
        ovr_local = override.get('local_tax') if override else None
        ovr_reason = override.get('reason') if override else None
        ovr_by = override.get('by') if override else None

        final_income = ovr_income if ovr_income is not None else calc_data['income_tax']
        final_local = ovr_local if ovr_local is not None else calc_data['local_tax']
        final_net = calc_data['total_payment'] - final_income - final_local

        existing = self._find_settlement_by_instructor_period(instructor_id, period)

        doc_data = {
            'instructor_id': str(instructor_id),
            'period': period,
            'industry_code': calc_data['industry_code'],
            'is_foreigner': calc_data['is_foreigner'],
            'total_payment': calc_data['total_payment'],
            'tax_rate': calc_data['tax_rate'],
            'calc_income_tax': calc_data['income_tax'],
            'calc_local_tax': calc_data['local_tax'],
            'calc_net_payment': calc_data['net_payment'],
            'is_submitted': 0,
            'updated_at': self._now_iso()
        }

        if existing:
            # 기존 override 보존 (재정산 시)
            existing_ovr_income = existing.get('ovr_income_tax')
            existing_ovr_local = existing.get('ovr_local_tax')

            doc_data['ovr_income_tax'] = existing_ovr_income if existing_ovr_income is not None else (ovr_income or '')
            doc_data['ovr_local_tax'] = existing_ovr_local if existing_ovr_local is not None else (ovr_local or '')
            doc_data['ovr_reason'] = existing.get('ovr_reason', ovr_reason or '')
            doc_data['ovr_by'] = existing.get('ovr_by', ovr_by or '')

            # final 계산: override 우선
            actual_ovr_income = existing_ovr_income if existing_ovr_income is not None and existing_ovr_income != '' else None
            actual_ovr_local = existing_ovr_local if existing_ovr_local is not None and existing_ovr_local != '' else None

            doc_data['final_income_tax'] = actual_ovr_income if actual_ovr_income is not None else calc_data['income_tax']
            doc_data['final_local_tax'] = actual_ovr_local if actual_ovr_local is not None else calc_data['local_tax']
            doc_data['final_net_payment'] = calc_data['total_payment'] - doc_data['final_income_tax'] - doc_data['final_local_tax']

            self.client.update_document(
                self._org(f'settlements/{existing["id"]}'), doc_data
            )
        else:
            doc_data['ovr_income_tax'] = ovr_income if ovr_income is not None else ''
            doc_data['ovr_local_tax'] = ovr_local if ovr_local is not None else ''
            doc_data['ovr_reason'] = ovr_reason or ''
            doc_data['ovr_at'] = self._now_iso() if ovr_reason else ''
            doc_data['ovr_by'] = ovr_by or ''
            doc_data['final_income_tax'] = final_income
            doc_data['final_local_tax'] = final_local
            doc_data['final_net_payment'] = final_net
            doc_data['created_at'] = self._now_iso()

            self.client.create_document(self._org('settlements'), doc_data)

    def apply_override(self, settlement_id,
                       income_tax: int, local_tax: int,
                       reason: str, user: str = ''):
        """수동 수정 적용 — final 값 즉시 갱신"""
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
        update_data = {
            'ovr_income_tax': income_tax,
            'ovr_local_tax': local_tax,
            'ovr_reason': reason,
            'ovr_at': self._now_iso(),
            'ovr_by': user,
            'final_income_tax': income_tax,
            'final_local_tax': local_tax,
            'final_net_payment': net,
            'updated_at': self._now_iso()
        }
        self.client.update_document(
            self._org(f'settlements/{settlement_id}'), update_data
        )

    def revert_override(self, settlement_id):
        """수동 수정 되돌리기 — final을 calc로 복원"""
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

        calc_income = settlement['calc_income_tax']
        calc_local = settlement['calc_local_tax']
        net = settlement['total_payment'] - calc_income - calc_local

        update_data = {
            'ovr_income_tax': '',
            'ovr_local_tax': '',
            'ovr_reason': '',
            'ovr_at': '',
            'ovr_by': '',
            'final_income_tax': calc_income,
            'final_local_tax': calc_local,
            'final_net_payment': net,
            'updated_at': self._now_iso()
        }
        self.client.update_document(
            self._org(f'settlements/{settlement_id}'), update_data
        )

    # ═══════════════════════════════════════════
    # 환경설정 (settings) — Key-Value
    # ═══════════════════════════════════════════

    def get_setting(self, key: str) -> dict | None:
        """설정값 조회"""
        doc = self.client.get_document(self._org(f'settings/{key}'))
        return doc

    def get_settings_by_category(self, category: str) -> list[dict]:
        """카테고리별 설정 목록"""
        docs = self.client.list_documents(
            self._org('settings'),
            filters=[('category', 'EQUAL', category)]
        )
        return docs

    def update_setting(self, key: str, value: str, is_encrypted: int = 0):
        """설정값 갱신 (없으면 생성)"""
        self.client.set_document(
            self._org(f'settings/{key}'),
            {
                'key': key,
                'value': value,
                'is_encrypted': is_encrypted,
                'category': self._get_setting_category(key),
                'updated_at': self._now_iso()
            }
        )

    def _get_setting_category(self, key: str) -> str:
        """설정 키에 따른 카테고리 자동 판별"""
        if key.startswith('org_'):
            return 'organization'
        elif key.startswith('cert_') or key.startswith('auth_') or key.startswith('simple_'):
            return 'auth'
        elif key.startswith('default_'):
            return 'defaults'
        return 'general'

    # ═══════════════════════════════════════════
    # 감사 로그 (audit_logs) — 내부용
    # ═══════════════════════════════════════════

    def _log_audit(self, action: str, table: str, target_id,
                   period: str = None, before: dict = None,
                   after: dict = None, reason: str = None, user: str = ''):
        """감사 로그 기록"""
        doc_data = {
            'action': action,
            'target_table': table,
            'target_id': str(target_id),
            'period': period or '',
            'before_json': json.dumps(before, ensure_ascii=False) if before else '',
            'after_json': json.dumps(after, ensure_ascii=False) if after else '',
            'reason': reason or '',
            'performed_by': user or self.auth.email or '',
            'performed_at': self._now_iso()
        }
        self.client.create_document(self._org('audit_logs'), doc_data)

    def get_audit_logs(self, period: str = None, limit: int = 50) -> list[dict]:
        """감사 로그 조회"""
        if period:
            docs = self.client.list_documents(
                self._org('audit_logs'),
                filters=[('period', 'EQUAL', period)]
            )
        else:
            docs = self.client.list_documents(self._org('audit_logs'))

        docs.sort(key=lambda x: x.get('performed_at', ''), reverse=True)
        return docs[:limit]

    # ═══════════════════════════════════════════
    # 연간 데이터 조회 (집계)
    # ═══════════════════════════════════════════

    def get_annual_summary(self, year: str, months: list[str] = None) -> list[dict]:
        """
        연간 합산 데이터 조회.
        Firestore에는 GROUP BY가 없으므로 파이썬에서 집계.
        """
        # 대상 기간 목록
        if months:
            periods = [f"{year}-{m}" for m in months]
        else:
            periods = [f"{year}-{m:02d}" for m in range(1, 13)]

        # 모든 정산 데이터 가져오기 (기간별)
        all_settlements = []
        for period in periods:
            settlements = self.client.list_documents(
                self._org('settlements'),
                filters=[('period', 'EQUAL', period)]
            )
            all_settlements.extend(settlements)

        if not all_settlements:
            return []

        # 강사 정보
        instructors_map = {}
        for inst in self.get_all_instructors():
            instructors_map[inst['id']] = inst

        # 강사별 집계
        summary = {}
        for stl in all_settlements:
            inst_id = stl.get('instructor_id', '')
            if inst_id not in summary:
                inst = instructors_map.get(inst_id, {})
                summary[inst_id] = {
                    'instructor_id': inst_id,
                    'name': inst.get('name', ''),
                    'resident_id': inst.get('resident_id', ''),
                    'industry_code': stl.get('industry_code', '940909'),
                    'annual_total': 0,
                    'annual_income_tax': 0,
                    'annual_local_tax': 0,
                    'annual_net_payment': 0,
                }
            s = summary[inst_id]
            s['annual_total'] += stl.get('total_payment', 0)
            s['annual_income_tax'] += stl.get('final_income_tax', 0)
            s['annual_local_tax'] += stl.get('final_local_tax', 0)
            s['annual_net_payment'] += stl.get('final_net_payment', 0)

        result = sorted(summary.values(), key=lambda x: x.get('name', ''))
        return result

    # ═══════════════════════════════════════════
    # 기관 정보 (organizations 문서 직접 접근)
    # ═══════════════════════════════════════════

    def get_org_info(self) -> dict | None:
        """기관 정보 조회"""
        return self.client.get_document(f'organizations/{self.org_id}')

    def update_org_info(self, data: dict):
        """기관 정보 수정"""
        self.client.update_document(f'organizations/{self.org_id}', data)
