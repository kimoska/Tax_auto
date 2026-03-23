"""
AutoTax — RPA 오케스트레이터
login → 메뉴 이동 → upload 파이프라인.
매 실행 시 깨끗한 브라우저 세션으로 시작 (세션 재사용 없음).
"""
import asyncio
import logging
import os

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class RPARunner:
    """
    RPA 실행 관리자.
    1. Playwright → Chromium (headless=False)
    2. 매번 깨끗한 브라우저 세션으로 시작
    3. HometaxLogin 으로 로그인
    4. HometaxUploader 로 엑셀 업로드
    5. 사용자에게 제출 확인 안내
    6. 브라우저 열어둠 (사용자가 확인/제출)
    """

    def __init__(self, auth_method: str = 'certificate', cert_keyword: str = '', cert_drive: str = 'C', cert_password: str = '', excel_path: str = ''):
        self.auth_method = auth_method
        self.cert_keyword = cert_keyword
        self.cert_drive = cert_drive
        self.cert_password = cert_password
        self.excel_path = excel_path
        self._progress_callback = None

    def set_progress_callback(self, callback):
        """진행 콜백: callback(step, total, message)"""
        self._progress_callback = callback

    def _emit(self, step: int, total: int, message: str):
        if self._progress_callback:
            self._progress_callback(step, total, message)
        logger.info(f'[RPA {step}/{total}] {message}')

    async def run(self) -> dict:
        """
        RPA 전체 파이프라인 실행.
        Returns: {'success': bool, 'message': str}
        """
        result = {'success': False, 'message': ''}

        if not self.excel_path or not os.path.exists(self.excel_path):
            result['message'] = f'엑셀 파일을 찾을 수 없습니다: {self.excel_path}'
            return result

        try:
            self._emit(1, 10, 'Playwright 브라우저 시작 중...')

            async with async_playwright() as pw:
                # Chromium 실행 (headless=False — 사용자가 화면 확인)
                browser = await pw.chromium.launch(
                    headless=False,
                    slow_mo=300,  # 안정성을 위한 딜레이
                    args=[
                        '--start-maximized',
                        '--disable-blink-features=AutomationControlled',
                        # 저 브라우저 권한 창(기기 액세스 허용)이 안 뜨게 하는 핵심 플래그
                        '--disable-features=BlockInsecurePrivateNetworkRequests',
                        '--disable-web-security',
                        '--allow-running-insecure-content',
                    ],
                )

                context = await self._create_context(browser)
                page = await context.new_page()

                # ── 로그인 검증 및 실행 ──
                self._emit(2, 10, '홈택스 자동 로그인 로직 시작...')
                # 홈택스 초기 화면은 이미 HometaxLogin이 감당함
                from rpa.hometax_login import HometaxLogin
                login_handler = HometaxLogin(
                    page, 
                    auth_method=self.auth_method,
                    cert_keyword=self.cert_keyword,
                    cert_drive=self.cert_drive,
                    cert_password=self.cert_password
                )

                def login_progress(step, total, msg):
                    mapped_step = 2 + int(step * 3 / total)
                    self._emit(mapped_step, 10, f'[로그인] {msg}')

                is_success = await login_handler.login(progress_callback=login_progress)
                if not is_success:
                    result['message'] = "로그인에 실패했습니다. 브라우저 화면을 확인하세요."
                    await self._keep_browser_open(page, browser)
                    return result
                
                # ── 2단계: 엑셀 업로드 ──
                self._emit(6, 10, '간이지급명세서 업로드 시작...')

                from rpa.hometax_uploader import HometaxUploader
                uploader = HometaxUploader(page)

                def upload_progress(step, total, msg):
                    mapped_step = 6 + int(step * 3 / total)
                    self._emit(mapped_step, 10, f'[업로드] {msg}')

                upload_success = await uploader.upload_excel(
                    self.excel_path,
                    progress_callback=upload_progress,
                )

                if upload_success:
                    result['success'] = True
                    result['message'] = (
                        '✅ 엑셀 업로드 완료!\n\n'
                        '⚠️ 중요:\n'
                        '1. 홈택스 화면에서 오류가 없는지 확인하세요.\n'
                        '2. 확인 후 [제출] 버튼을 직접 클릭하세요.\n'
                        '3. 제출 후 접수증을 다운로드/보관하세요.\n\n'
                        '브라우저를 닫지 마세요!'
                    )
                else:
                    result['message'] = (
                        '엑셀 업로드 과정에서 문제가 발생했습니다.\n'
                        '브라우저 화면을 확인하고 수동으로 진행해주세요.'
                    )

                self._emit(10, 10, '완료 — 브라우저에서 확인 후 제출하세요')
                await self._keep_browser_open(page, browser)

        except Exception as e:
            logger.error(f'RPA 실행 오류: {e}')
            result['message'] = f'RPA 실행 중 오류가 발생했습니다:\n{str(e)}'

        return result

    async def _create_context(self, browser):
        """브라우저 컨텍스트 생성 (항상 깨끗한 세션으로 시작)"""
        context_opts = {
            'viewport': {'width': 1280, 'height': 900},
            'locale': 'ko-KR',
            'timezone_id': 'Asia/Seoul',
        }
        
        # [수정] 기존 세션 복원 로직 제거 (사용자 요청: 이전 기록이 방해하지 않도록)
        # if os.path.exists(SESSION_FILE): ... 제거

        return await browser.new_context(**context_opts)

    async def _save_session(self, context):
        """로그인 세션 저장 로직 제거 (항상 새로운 로그인 보장)"""
        pass

    async def _keep_browser_open(self, page, browser):
        """브라우저를 열어둔 채 사용자 확인 대기 (5분)"""
        try:
            await page.wait_for_timeout(300_000)  # 5분
        except Exception:
            pass
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    def run_sync(self) -> dict:
        """동기 래퍼 (GUI 스레드에서 호출용)"""
        return asyncio.run(self.run())
