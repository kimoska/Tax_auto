"""
AutoTax — 홈택스 엑셀 업로더 (2차 검증 반영)
핵심 수정: GNB 메뉴는 hover 필요, dispatchEvent/click({force:true}) 적용.
"""
import os
import logging

logger = logging.getLogger(__name__)


class HometaxUploader:
    """
    홈택스 간이지급명세서(사업소득) 엑셀 업로드.
    로그인 완료 후 호출.

    검증된 메뉴 경로:
      GNB: "지급명세·자료·공익법인" → #mf_wfHeader_wq_uuid_438 (hover 필요)
      2depth: LI #mf_wfHeader_hdGroup918 (부모)
      3depth: "직접작성 제출" → #menuAtag_4401100000
    """

    MAIN_URL = 'https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml'

    def __init__(self, page):
        self.page = page

    async def upload_excel(self, excel_path: str, progress_callback=None) -> bool:
        if not os.path.exists(excel_path):
            self._emit(progress_callback, 1, 5, f'❌ 파일 없음: {excel_path}')
            return False

        total = 5
        try:
            # ── 1: 메인 페이지로 이동 (로그인 후 리다이렉트 대응) ──
            self._emit(progress_callback, 1, total,
                       '홈택스 메인 페이지로 이동...')
            await self.page.goto(self.MAIN_URL,
                                 wait_until='domcontentloaded', timeout=30000)
            await self.page.wait_for_timeout(3000)

            # ── 2: GNB 메뉴 → 직접작성 제출 ──
            self._emit(progress_callback, 2, total,
                       '[지급명세·자료·공익법인] → [직접작성 제출]...')
            await self._navigate_to_direct_submit()

            # ── 3: 간이지급명세서(거주자의 사업소득) 선택 ──
            self._emit(progress_callback, 3, total,
                       '[간이지급명세서(거주자의 사업소득)] 선택 중...')
            await self._select_income_type()

            # ── 4: 엑셀 파일 업로드 ──
            self._emit(progress_callback, 4, total,
                       '엑셀 파일 업로드 중...')
            await self._upload_file(excel_path)

            # ── 5: 완료 ──
            self._emit(progress_callback, 5, total,
                       '✅ 업로드 완료! 오류 여부 확인 후 [제출] 버튼을 직접 클릭하세요.')
            return True

        except Exception as e:
            logger.error(f'홈택스 업로드 실패: {e}')
            self._emit(progress_callback, total, total, f'❌ 오류: {str(e)[:80]}')
            return False

    async def _navigate_to_direct_submit(self):
        """
        GNB 메뉴 이동: 지급명세 → 직접작성 제출.
        GNB 드롭다운은 hover로 나타나므로 hover → click 순서.
        """
        success = False

        # ─── 방법 1: GNB hover → 하위메뉴 클릭 ───
        try:
            # 1depth: "지급명세·자료·공익법인" 부모 LI에 hover
            gnb_parent = self.page.locator('#mf_wfHeader_hdGroup918')
            gnb_link = self.page.locator('#mf_wfHeader_wq_uuid_438')

            # hover로 드롭다운 활성화
            await gnb_parent.hover(timeout=5000)
            await self.page.wait_for_timeout(1000)

            # 텍스트로도 시도
            if not await gnb_link.is_visible(timeout=1000):
                gnb_link = self.page.locator('a:has-text("지급명세·자료·공익법인")').first

            await gnb_link.hover()
            await self.page.wait_for_timeout(1000)

            # "직접작성 제출" 하위 메뉴 클릭
            direct = self.page.locator('#menuAtag_4401100000')
            if await direct.is_visible(timeout=3000):
                await direct.click()
                await self.page.wait_for_timeout(3000)
                logger.info('GNB hover → 직접작성 제출 클릭 성공')
                success = True
        except Exception as e:
            logger.debug(f'GNB hover 방식 실패: {e}')

        # ─── 방법 2: JavaScript로 강제 클릭 ───
        if not success:
            try:
                await self.page.evaluate('''() => {
                    const el = document.getElementById('menuAtag_4401100000');
                    if (el) { el.click(); return true; }
                    return false;
                }''')
                await self.page.wait_for_timeout(3000)
                logger.info('JS 강제 클릭으로 직접작성 제출 이동')
                success = True
            except Exception as e:
                logger.debug(f'JS 클릭 실패: {e}')

        # ─── 방법 3: force click (Playwright) ───
        if not success:
            try:
                direct = self.page.locator('#menuAtag_4401100000')
                await direct.click(force=True, timeout=5000)
                await self.page.wait_for_timeout(3000)
                logger.info('force click으로 직접작성 제출 이동')
                success = True
            except Exception as e:
                logger.debug(f'force click 실패: {e}')

        # ─── 방법 4: 전체메뉴 경유 ───
        if not success:
            try:
                await self.page.locator('#mf_wfHeader_hdGroup005').click()
                await self.page.wait_for_timeout(2000)

                tab = self.page.locator(
                    '#mf_wfHeader_UTXPPBAD22_wframe_wq_uuid_989_tab_tabs5_tabHTML')
                if await tab.is_visible(timeout=3000):
                    await tab.click()
                    await self.page.wait_for_timeout(2000)
                    logger.info('전체메뉴 → 지급명세 탭 경유')
                    success = True
            except Exception as e:
                logger.debug(f'전체메뉴 경유 실패: {e}')

        if not success:
            logger.warning('모든 메뉴 이동 방법 실패')

    async def _select_income_type(self):
        """간이지급명세서(거주자의 사업소득) 선택 + 일괄등록"""
        # 소득자료 종류 선택 화면 (로그인 후에만 접근 가능 → 셀렉터는 텍스트 기반)
        income_sels = [
            'text=간이지급명세서(거주자의 사업소득)',
            'text=거주자의 사업소득',
            'a:has-text("거주자의 사업소득")',
            'span:has-text("거주자의 사업소득")',
            'text=간이지급명세서',
        ]
        await self._try_click(income_sels, '거주자의 사업소득')
        await self.page.wait_for_timeout(2000)

        # 확인/선택 버튼
        await self._try_click(
            ['text=선택하기', 'text=확인', 'text=다음',
             'button:has-text("확인")', 'button:has-text("선택")'],
            '확인 버튼')
        await self.page.wait_for_timeout(2000)

        # 일괄등록
        await self._try_click(
            ['text=일괄등록', 'text=엑셀 업로드', 'a:has-text("일괄")',
             'button:has-text("일괄")', 'span:has-text("일괄등록")'],
            '일괄등록')
        await self.page.wait_for_timeout(2000)

    async def _upload_file(self, filepath: str):
        """엑셀 파일 업로드 (input[type=file] 우선, file_chooser 차선)"""
        abs_path = os.path.abspath(filepath)

        # 방법 1: input[type=file]
        file_inputs = self.page.locator('input[type="file"]')
        if await file_inputs.count() > 0:
            await file_inputs.first.set_input_files(abs_path)
            await self.page.wait_for_timeout(3000)
            await self._try_click(
                ['text=업로드', 'text=확인', 'button:has-text("업로드")'],
                '업로드 확인')
            return

        # 방법 2: 파일 버튼 → file_chooser
        for sel in ['text=파일첨부', 'text=찾아보기', 'text=파일선택',
                    'button:has-text("파일")', 'button:has-text("찾아보기")']:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=2000):
                    async with self.page.expect_file_chooser(timeout=10000) as fc:
                        await loc.click()
                    chooser = await fc.value
                    await chooser.set_files(abs_path)
                    await self.page.wait_for_timeout(3000)
                    await self._try_click(['text=업로드', 'text=확인'], '업로드 확인')
                    return
            except Exception:
                continue

        logger.warning('파일 input 못 찾음 → 사용자가 직접 업로드해주세요')

    async def _try_click(self, selectors: list, label: str) -> bool:
        for sel in selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.is_visible(timeout=2000):
                    await loc.click()
                    logger.info(f'[{label}] 클릭: {sel}')
                    return True
            except Exception:
                continue
        logger.warning(f'[{label}] 클릭 실패')
        return False

    @staticmethod
    def _emit(cb, step, total, msg):
        if cb:
            cb(step, total, msg)
