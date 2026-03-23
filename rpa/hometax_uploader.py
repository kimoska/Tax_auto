"""
AutoTax — 홈택스 상세내역 양방향 동기화
프로그램 정산 데이터 ↔ 홈택스 목록을 일치시킴
"""
import os
import logging

logger = logging.getLogger(__name__)

# 요소 ID 접두사 (반복 방지)
P = 'mf_txppWframe_wfDetailBrkd'

# 업종코드 → 한글명 매핑 (홈택스 검색용)
INDUSTRY_CODE_NAMES = {
    '940902': '꽃꽂이교사',
    '940909': '기타자영업',
}


class HometaxUploader:
    MAIN_URL = 'https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml'

    def __init__(self, page):
        self.page = page

    async def upload_excel(self, excel_path: str, settlements: list = None, progress_callback=None) -> bool:
        if not os.path.exists(excel_path):
            self._emit(progress_callback, 1, 8, f'❌ 파일 없음: {excel_path}')
            return False

        total = 8
        try:
            self._emit(progress_callback, 1, total, '홈택스 메인 페이지로 이동...')
            await self.page.goto(self.MAIN_URL, wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(3000)

            self._emit(progress_callback, 2, total, '[지급명세·자료·공익법인] → [직접작성 제출]...')
            await self._navigate_to_direct_submit()

            self._emit(progress_callback, 3, total, '[간이지급명세서(거주자의 사업소득)] 선택 중...')
            await self._select_income_type()

            self._emit(progress_callback, 4, total, '[상세내역 작성하기] 클릭...')
            await self._click_write_details()

            if settlements:
                self._emit(progress_callback, 5, total,
                           f'📝 홈택스 ↔ 프로그램 동기화 시작 ({len(settlements)}명)...')
                result = await self._sync_with_hometax(settlements, progress_callback, total)
                self._last_sync_result = result
                self._emit(progress_callback, total, total,
                           f'✅ 동기화 완료! 수정:{result["updated"]} 삭제:{result["deleted"]} 신규:{result["added"]}')
            else:
                self._emit(progress_callback, 5, total, '정산 데이터 없음')

            return True
        except Exception as e:
            logger.error(f'홈택스 업로드 실패: {e}', exc_info=True)
            self._emit(progress_callback, total, total, f'❌ 오류: {str(e)[:80]}')
            return False

    # ═══════════════════════════════════════════════════════════
    # 핵심: 양방향 동기화
    # ═══════════════════════════════════════════════════════════

    async def _sync_with_hometax(self, settlements, progress_callback, total_steps):
        """프로그램 데이터와 홈택스 목록 양방향 동기화"""
        result = {'updated': 0, 'deleted': 0, 'added': 0, 'details': []}

        # ── Phase 1: 홈택스 목록 전체 스캔 ──
        self._emit(progress_callback, 5, total_steps, '🔍 홈택스 목록 스캔 중...')
        hometax_entries = await self._scan_all_hometax_entries()
        logger.info(f"홈택스 스캔 완료: {len(hometax_entries)}건")

        # ── Phase 2: 매칭 & 분류 ──
        self._emit(progress_callback, 6, total_steps, '🔄 매칭 분류 중...')

        # 프로그램 매칭 dict: (주민번호 앞6자리, 전체이름) → settlement
        prog_dict = {}
        for s in settlements:
            rid = s.get('resident_id', '').replace('-', '')
            name = s.get('name', '')
            if len(rid) >= 6 and name:
                key = (rid[:6], name)
                prog_dict[key] = s
                logger.info(f"  프로그램: {name} key=({rid[:6]}, {name}) 지급액={s['total_payment']:,}")

        matched = []       # (hometax_entry, settlement)
        to_delete = []     # hometax_entry (프로그램에 없음)
        matched_prog_keys = set()

        for ht in hometax_entries:
            ht_key = (ht['rid_prefix'], ht['full_name'])
            if ht_key in prog_dict:
                matched.append((ht, prog_dict[ht_key]))
                matched_prog_keys.add(ht_key)
                logger.info(f"  매칭 ✔: {ht['full_name']} (홈택스) ↔ {prog_dict[ht_key]['name']} (프로그램)")
            else:
                to_delete.append(ht)
                logger.info(f"  삭제 대상: {ht['full_name']} (홈택스에만 있음)")

        to_add = []  # 프로그램에만 있는 항목
        for key, s in prog_dict.items():
            if key not in matched_prog_keys:
                to_add.append(s)
                logger.info(f"  신규 등록 대상: {s['name']} (프로그램에만 있음)")

        logger.info(f"분류 결과: 수정={len(matched)}, 삭제={len(to_delete)}, 신규={len(to_add)}")

        # ── Phase 3a: 기존 항목 지급액 수정 ──
        self._emit(progress_callback, 6, total_steps,
                   f'✏️ 기존 {len(matched)}건 지급액 수정 중...')
        for ht_entry, settlement in matched:
            try:
                ok = await self._update_existing_entry(ht_entry, settlement)
                if ok:
                    result['updated'] += 1
                    old_amt = ht_entry.get('old_amount', 0)
                    new_amt = settlement['total_payment']
                    result['details'].append(
                        f"✏️ {settlement['name']}: 지급액 {old_amt:,}원 → {new_amt:,}원"
                    )
            except Exception as e:
                logger.error(f"  수정 실패 ({settlement['name']}): {e}")

        # ── Phase 3b: 불일치 항목 삭제 ──
        if to_delete:
            self._emit(progress_callback, 7, total_steps,
                       f'🗑️ 불일치 {len(to_delete)}건 삭제 중...')
            deleted = await self._delete_unmatched_entries(to_delete)
            result['deleted'] = deleted
            for entry in to_delete:
                result['details'].append(
                    f"🗑️ {entry['full_name']}: 삭제 (프로그램에 없음)"
                )

        # ── Phase 3c: 신규 항목 등록 ──
        if to_add:
            self._emit(progress_callback, 7, total_steps,
                       f'➕ 신규 {len(to_add)}건 등록 중...')
            for settlement in to_add:
                try:
                    ok = await self._create_new_entry(settlement)
                    if ok:
                        result['added'] += 1
                        code_name = INDUSTRY_CODE_NAMES.get(
                            settlement.get('industry_code', ''), '기타')
                        result['details'].append(
                            f"➕ {settlement['name']}: 신규등록 ({code_name}, {settlement['total_payment']:,}원)"
                        )
                except Exception as e:
                    logger.error(f"  신규등록 실패 ({settlement['name']}): {e}")

        return result

    # ───────────────────────────────────────────
    # Phase 1: 홈택스 목록 전체 스캔
    # ───────────────────────────────────────────

    async def _scan_all_hometax_entries(self):
        """모든 페이지의 행을 스캔하여 (rid_prefix, full_name, row_index, page) 수집"""
        entries = []
        page_num = 1

        while True:
            logger.info(f"═══ 스캔: 페이지 {page_num} ═══")
            await self.page.wait_for_timeout(2000)

            # 현재 페이지의 수정 버튼 셀 수
            row_count = await self.page.evaluate('''() => {
                return document.querySelectorAll('td[data-col_id="modifyGrdData"]').length;
            }''')
            logger.info(f"  행 수: {row_count}")

            if row_count == 0:
                break

            for row_idx in range(row_count):
                # 그리드에서 주민번호 읽기
                rid_from_grid = await self.page.evaluate('''(idx) => {
                    const cells = document.querySelectorAll('td[data-col_id="modifyGrdData"]');
                    if (!cells[idx]) return '';
                    const tr = cells[idx].closest('tr');
                    if (!tr) return '';
                    const tds = Array.from(tr.querySelectorAll('td'));
                    for (const td of tds) {
                        const text = td.textContent.trim();
                        if (text.match(/^\\d{6}[\\-\\*]/)) return text;
                    }
                    return '';
                }''', row_idx)

                rid_prefix = rid_from_grid.replace('-', '').replace('*', '')[:6]

                # "수정" 클릭하여 전체 이름 읽기
                await self.page.evaluate('''(idx) => {
                    const cells = document.querySelectorAll('td[data-col_id="modifyGrdData"]');
                    if (cells[idx]) {
                        const btn = cells[idx].querySelector('button');
                        if (btn) btn.click();
                    }
                }''', row_idx)
                await self.page.wait_for_timeout(1500)

                # 폼에서 전체 이름 + 기존 지급액 읽기
                form_data = await self.page.evaluate(f'''() => {{
                    const nameEl = document.getElementById('{P}_edtIeNm');
                    const payEl = document.getElementById('{P}_edtTotaPymnAmt');
                    return {{
                        name: nameEl ? nameEl.value : '',
                        amount: payEl ? payEl.value.replace(/,/g, '') : '0'
                    }};
                }}''')
                full_name = form_data.get('name', '')
                old_amount = int(form_data.get('amount', '0') or '0')

                if rid_prefix and full_name:
                    entries.append({
                        'rid_prefix': rid_prefix,
                        'full_name': full_name,
                        'rid_from_grid': rid_from_grid,
                        'old_amount': old_amount,
                        'page': page_num,
                        'row_idx_in_page': row_idx,
                    })
                    logger.info(f"  [{len(entries)}] {full_name} ({rid_prefix}***) 기존 지급액={old_amount:,}")

            # 다음 페이지 확인
            has_next = await self._go_to_next_page(page_num)
            if not has_next:
                break
            page_num += 1

        # 1페이지로 복귀
        if page_num > 1:
            await self._go_to_page(1)

        return entries

    # ───────────────────────────────────────────
    # Phase 3a: 기존 항목 수정
    # ───────────────────────────────────────────

    async def _update_existing_entry(self, ht_entry, settlement):
        """매칭된 홈택스 항목의 지급액 수정"""
        name = settlement['name']
        new_amount = settlement['total_payment']
        target_page = ht_entry['page']
        target_row = ht_entry['row_idx_in_page']

        logger.info(f"  수정 시작: {name} → {new_amount:,}원 (page={target_page}, row={target_row})")

        # 해당 페이지로 이동
        await self._go_to_page(target_page)
        await self.page.wait_for_timeout(1000)

        # "수정" 클릭
        await self.page.evaluate('''(idx) => {
            const cells = document.querySelectorAll('td[data-col_id="modifyGrdData"]');
            if (cells[idx]) {
                const btn = cells[idx].querySelector('button');
                if (btn) btn.click();
            }
        }''', target_row)
        await self.page.wait_for_timeout(2000)

        # 지급액 입력
        pay_input = self.page.locator(f'#{P}_edtTotaPymnAmt')
        try:
            await pay_input.wait_for(state='visible', timeout=5000)
            await pay_input.click(click_count=3)
            await self.page.wait_for_timeout(300)
            await pay_input.fill(str(new_amount))
            await self.page.wait_for_timeout(500)
            await pay_input.press('Tab')
            await self.page.wait_for_timeout(1000)
        except Exception as e:
            logger.error(f"  지급액 입력 실패: {e}")
            return False

        # 등록하기
        try:
            reg_btn = self.page.locator(f'#{P}_btnAddRow')
            await reg_btn.wait_for(state='visible', timeout=5000)
            await reg_btn.click()
            await self.page.wait_for_timeout(3000)
            await self._handle_alert_popup()
            logger.info(f"  ✔ {name} 수정 완료 ({new_amount:,}원)")
            return True
        except Exception as e:
            logger.error(f"  등록하기 실패: {e}")
            return False

    # ───────────────────────────────────────────
    # Phase 3b: 불일치 항목 삭제
    # ───────────────────────────────────────────

    async def _delete_unmatched_entries(self, to_delete):
        """프로그램에 없는 홈택스 항목 삭제"""
        deleted = 0

        # 페이지별로 그룹핑
        by_page = {}
        for entry in to_delete:
            pg = entry['page']
            if pg not in by_page:
                by_page[pg] = []
            by_page[pg].append(entry)

        for page_num in sorted(by_page.keys()):
            await self._go_to_page(page_num)
            await self.page.wait_for_timeout(1500)

            entries_in_page = by_page[page_num]
            for entry in entries_in_page:
                row_idx = entry['row_idx_in_page']
                # 체크박스 클릭 (그리드 첫 번째 컬럼)
                await self.page.evaluate('''(idx) => {
                    const editCells = document.querySelectorAll('td[data-col_id="modifyGrdData"]');
                    if (!editCells[idx]) return;
                    const tr = editCells[idx].closest('tr');
                    if (!tr) return;
                    const checkbox = tr.querySelector('input[type="checkbox"]');
                    if (checkbox && !checkbox.checked) checkbox.click();
                }''', row_idx)
                await self.page.wait_for_timeout(500)
                logger.info(f"  체크: {entry['full_name']} (page={page_num}, row={row_idx})")

        # 선택자료삭제 클릭
        try:
            del_btn = self.page.locator(f'#{P}_btnDelete')
            await del_btn.wait_for(state='visible', timeout=5000)
            await del_btn.click()
            await self.page.wait_for_timeout(2000)
            await self._handle_alert_popup()
            deleted = len(to_delete)
            logger.info(f"  ✔ {deleted}건 삭제 완료")
        except Exception as e:
            logger.error(f"  선택자료삭제 실패: {e}")

        return deleted

    # ───────────────────────────────────────────
    # Phase 3c: 신규 항목 등록
    # ───────────────────────────────────────────

    async def _create_new_entry(self, settlement):
        """프로그램에만 있는 항목을 홈택스에 신규 등록"""
        name = settlement['name']
        rid = settlement.get('resident_id', '').replace('-', '')
        amount = settlement['total_payment']
        industry = settlement.get('industry_code', '940909')
        is_foreigner = settlement.get('is_foreigner', '1')
        period = settlement.get('period', '')

        if len(period) >= 7:
            year = period[:4]
            month = period[5:7].lstrip('0')  # "02" → "2"
        else:
            logger.error(f"  period 형식 오류: {period}")
            return False

        logger.info(f"  신규등록 시작: {name} ({rid[:6]}***) 지급액={amount:,} 업종={industry}")

        # 1. "전체 새로작성하기" 클릭
        await self.page.evaluate(f'''() => {{
            const btn = document.getElementById('{P}_btnClear');
            if (btn) btn.click();
        }}''')
        await self.page.wait_for_timeout(2000)
        await self._handle_alert_popup()
        await self.page.wait_for_timeout(1000)

        # 2. 내/외국인 선택 (is_foreigner='1'은 내국인, '2'는 외국인)
        if is_foreigner == '2':
            await self.page.evaluate(f'''() => {{
                const label = document.querySelector('label[for="{P}_nnfClCd_input_1"]');
                if (label) label.click();
            }}''')
            await self.page.wait_for_timeout(500)
            logger.info(f"  → 외국인 선택")

        # 3. 주민번호 입력 (하이픈 없이 13자리)
        ie_no_input = self.page.locator(f'#{P}_edtIeNo1')
        try:
            await ie_no_input.wait_for(state='visible', timeout=5000)
            await ie_no_input.click()
            await ie_no_input.fill(rid)
            await self.page.wait_for_timeout(500)
            logger.info(f"  → 주민번호 입력: {rid[:6]}*******")
        except Exception as e:
            logger.error(f"  주민번호 입력 실패: {e}")
            return False

        # 4. 확인 버튼
        await self.page.evaluate(f'''() => {{
            const btn = document.getElementById('{P}_btnIeNoChk');
            if (btn) btn.click();
        }}''')
        await self.page.wait_for_timeout(2000)
        await self._handle_alert_popup()
        await self.page.wait_for_timeout(1000)

        # 5. 성명 입력
        name_input = self.page.locator(f'#{P}_edtIeNm')
        try:
            await name_input.wait_for(state='visible', timeout=5000)
            await name_input.click()
            await name_input.fill(name)
            await self.page.wait_for_timeout(500)
            logger.info(f"  → 성명 입력: {name}")
        except Exception as e:
            logger.error(f"  성명 입력 실패: {e}")
            return False

        # 6. 업종코드 검색 (한글명으로 검색)
        code_name = INDUSTRY_CODE_NAMES.get(industry, '기타자영업')
        await self._search_industry_code(code_name)

        # 7. 귀속연도 선택 (드롭다운)
        try:
            year_select = self.page.locator(f'#{P}_attrYr_A0162')
            if await year_select.count() > 0:
                await year_select.select_option(value=year)
                await self.page.wait_for_timeout(500)
                logger.info(f"  → 귀속연도: {year}")
        except Exception as e:
            logger.debug(f"  귀속연도 선택 시도: {e}")

        # 8. 귀속월 선택 (드롭다운)
        try:
            month_select = self.page.locator(f'#{P}_cmbAttrMm')
            if await month_select.count() > 0:
                await month_select.select_option(value=month)
                await self.page.wait_for_timeout(500)
                logger.info(f"  → 귀속월: {month}")
        except Exception as e:
            logger.debug(f"  귀속월 선택 시도: {e}")

        # 9. 지급액 입력
        pay_input = self.page.locator(f'#{P}_edtTotaPymnAmt')
        try:
            await pay_input.wait_for(state='visible', timeout=5000)
            await pay_input.click(click_count=3)
            await self.page.wait_for_timeout(300)
            await pay_input.fill(str(amount))
            await self.page.wait_for_timeout(500)
            await pay_input.press('Tab')
            await self.page.wait_for_timeout(1000)
            logger.info(f"  → 지급액: {amount:,}")
        except Exception as e:
            logger.error(f"  지급액 입력 실패: {e}")
            return False

        # 10. 등록하기
        try:
            reg_btn = self.page.locator(f'#{P}_btnAddRow')
            await reg_btn.wait_for(state='visible', timeout=5000)
            await reg_btn.click()
            await self.page.wait_for_timeout(3000)
            await self._handle_alert_popup()
            logger.info(f"  ✔ {name} 신규등록 완료")
            return True
        except Exception as e:
            logger.error(f"  등록하기 실패: {e}")
            return False

    async def _search_industry_code(self, korean_name: str):
        """업종코드 검색 팝업에서 한글명으로 검색하여 선택"""
        # 검색 버튼 클릭
        await self.page.evaluate(f'''() => {{
            const btn = document.getElementById('{P}_btnBsicTfbCd');
            if (btn) btn.click();
        }}''')
        await self.page.wait_for_timeout(2000)

        # 검색어(한글 업종명) 입력
        search_input = self.page.locator(f'#{P}_UTECMAAA06_wframe_edtCdVvalKrnNm')
        try:
            await search_input.wait_for(state='visible', timeout=5000)
            await search_input.click()
            await search_input.fill(korean_name)
            await self.page.wait_for_timeout(500)
        except Exception as e:
            logger.error(f"  업종코드 검색어 입력 실패: {e}")
            return

        # 조회 클릭
        await self.page.evaluate(f'''() => {{
            const btn = document.getElementById('{P}_UTECMAAA06_wframe_btnSch1');
            if (btn) btn.click();
        }}''')
        await self.page.wait_for_timeout(2000)

        # 첫 번째 결과 선택
        await self.page.evaluate('''() => {
            const btn = document.querySelector('button[title="선택"]');
            if (btn) btn.click();
        }''')
        await self.page.wait_for_timeout(1000)

        # 닫기
        await self.page.evaluate(f'''() => {{
            const btn = document.getElementById('{P}_UTECMAAA06_wframe_trigger2');
            if (btn) btn.click();
        }}''')
        await self.page.wait_for_timeout(1000)
        logger.info(f"  → 업종코드 '{korean_name}' 설정 완료")

    # ───────────────────────────────────────────
    # 페이지 이동 유틸
    # ───────────────────────────────────────────

    async def _go_to_page(self, page_num: int):
        """특정 페이지로 이동"""
        if page_num == 1:
            page_id = f'{P}_pglNavi1_page_1'
        else:
            page_id = f'{P}_pglNavi1_page_{page_num}'

        clicked = await self.page.evaluate('''(pageId) => {
            const el = document.getElementById(pageId);
            if (el) { el.click(); return true; }
            return false;
        }''', page_id)

        if clicked:
            await self.page.wait_for_timeout(2000)
            logger.info(f"  페이지 {page_num}로 이동")
        return clicked

    async def _go_to_next_page(self, current_page: int) -> bool:
        """다음 페이지로 이동"""
        next_page = current_page + 1
        page_id = f'{P}_pglNavi1_page_{next_page}'

        try:
            link = self.page.locator(f'#{page_id}')
            if await link.count() > 0 and await link.is_visible(timeout=2000):
                await link.click()
                await self.page.wait_for_timeout(2000)
                logger.info(f"  페이지 {next_page}로 이동")
                return True

            clicked = await self.page.evaluate('''(pageId) => {
                const el = document.getElementById(pageId);
                if (el) { el.click(); return true; }
                return false;
            }''', page_id)
            if clicked:
                await self.page.wait_for_timeout(2000)
                return True
        except Exception:
            pass
        return False

    # ───────────────────────────────────────────
    # 공통 유틸
    # ───────────────────────────────────────────

    async def _handle_alert_popup(self):
        """확인/알림 팝업 자동 처리"""
        try:
            for selector in [
                'button:has-text("확인")',
                '.w2alert button',
                '.w2confirm button:has-text("확인")',
            ]:
                btn = self.page.locator(selector).first
                try:
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        await self.page.wait_for_timeout(1000)
                        logger.info("  팝업 확인")
                        return
                except Exception:
                    continue
        except Exception:
            pass

    # ───────────────────────────────────────────
    # 메뉴 이동 (기존 — 수정 없음)
    # ───────────────────────────────────────────

    async def _navigate_to_direct_submit(self):
        success = False
        try:
            gnb_parent = self.page.locator('#mf_wfHeader_hdGroup918')
            gnb_link = self.page.locator('#mf_wfHeader_wq_uuid_438')
            await gnb_parent.hover(timeout=5000)
            await self.page.wait_for_timeout(1000)
            if not await gnb_link.is_visible(timeout=1000):
                gnb_link = self.page.locator('a:has-text("지급명세·자료·공익법인")').first
            await gnb_link.hover()
            await self.page.wait_for_timeout(1000)
            direct = self.page.locator('#menuAtag_4401100000')
            if await direct.is_visible(timeout=3000):
                await direct.click()
                await self.page.wait_for_timeout(3000)
                logger.info('GNB hover → 직접작성 제출 클릭 성공')
                success = True
        except Exception as e:
            logger.debug(f'GNB hover 실패: {e}')

        if not success:
            try:
                await self.page.evaluate('''() => {
                    const el = document.getElementById('menuAtag_4401100000');
                    if (el) { el.click(); return true; }
                    return false;
                }''')
                await self.page.wait_for_timeout(3000)
                logger.info('JS 클릭으로 직접작성 제출 이동')
                success = True
            except Exception as e:
                logger.debug(f'JS 클릭 실패: {e}')

        if not success:
            try:
                direct = self.page.locator('#menuAtag_4401100000')
                await direct.click(force=True, timeout=5000)
                await self.page.wait_for_timeout(3000)
                success = True
            except Exception as e:
                logger.debug(f'force click 실패: {e}')

        if not success:
            logger.warning('모든 메뉴 이동 방법 실패')

    async def _select_income_type(self):
        try:
            select_box = self.page.locator('#mf_txppWframe_mateKndCd')
            if await select_box.is_visible(timeout=10000):
                await select_box.select_option(label='간이지급명세서(거주자의 사업소득)')
                logger.info('[지급명세서 선택] 완료')
                await self.page.wait_for_timeout(2000)
            else:
                await self.page.evaluate('''() => {
                    const sel = document.getElementById('mf_txppWframe_mateKndCd');
                    if (sel) {
                        for (let i = 0; i < sel.options.length; i++) {
                            if (sel.options[i].text.includes('거주자의 사업소득')) {
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {bubbles: true}));
                                break;
                            }
                        }
                    }
                }''')
                await self.page.wait_for_timeout(2000)
        except Exception as e:
            logger.warning(f'지급명세서 드롭다운 선택 실패: {e}')

    async def _click_write_details(self):
        try:
            btn = self.page.locator('#mf_txppWframe_btnDpclWrt')
            if await btn.is_visible(timeout=5000):
                await btn.click(force=True)
                logger.info("상세내역 작성하기 버튼 클릭 완료!")
                await self.page.wait_for_timeout(5000)
                await self._handle_alert_popup()
            else:
                logger.warning("상세내역 작성하기 버튼이 보이지 않습니다.")
        except Exception as e:
            logger.warning(f'상세내역 작성하기 오류: {e}')

    @staticmethod
    def _emit(cb, step, total, msg):
        if cb:
            cb(step, total, msg)
