"""
AutoTax — RPA 단독 테스트 스크립트
홈택스에 접속하여 실제 페이지 구조를 확인하고 셀렉터를 테스트합니다.

사용법:
  python test_rpa.py login        # 로그인만 테스트
  python test_rpa.py navigate     # 로그인 + 간이지급명세서 메뉴 이동 테스트
  python test_rpa.py full <경로>  # 전체 파이프라인 (로그인→메뉴→업로드)
  python test_rpa.py inspect      # 현재 페이지 셀렉터 탐색 (디버그용)
"""
import asyncio
import sys
import os
import logging

# 프로젝트 루트를 Python path에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)


def progress(step, total, msg):
    bar = '█' * step + '░' * (total - step)
    print(f'  [{bar}] {step}/{total} {msg}')


async def test_login():
    """로그인만 테스트"""
    from playwright.async_api import async_playwright
    from rpa.hometax_login import HometaxLogin

    print('\n=== 홈택스 로그인 테스트 ===')
    print('인증서 또는 간편인증을 직접 완료해주세요.\n')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=300,
            args=['--start-maximized'],
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
        )
        page = await context.new_page()

        login = HometaxLogin(page, auth_method='certificate')
        success = await login.login(progress_callback=progress)

        if success:
            print('\n✅ 로그인 성공!')
            print('현재 URL:', page.url)

            # 세션 저장
            os.makedirs('.hometax_session', exist_ok=True)
            await context.storage_state(path='.hometax_session/state.json')
            print('세션 저장 완료: .hometax_session/state.json')
        else:
            print('\n❌ 로그인 실패')

        print('\n브라우저를 30초 후 닫습니다. Ctrl+C로 중지 가능.')
        await page.wait_for_timeout(30000)
        await browser.close()


async def test_navigate():
    """로그인 + 간이지급명세서 메뉴 이동 테스트"""
    from playwright.async_api import async_playwright
    from rpa.hometax_login import HometaxLogin
    from rpa.hometax_uploader import HometaxUploader

    print('\n=== 홈택스 메뉴 이동 테스트 ===')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False, slow_mo=300,
            args=['--start-maximized'],
        )

        # 세션 복원 시도
        ctx_opts = {'viewport': {'width': 1280, 'height': 900}, 'locale': 'ko-KR'}
        if os.path.exists('.hometax_session/state.json'):
            ctx_opts['storage_state'] = '.hometax_session/state.json'
            print('이전 세션 복원 중...')

        context = await browser.new_context(**ctx_opts)
        page = await context.new_page()

        # 로그인
        login = HometaxLogin(page, auth_method='certificate')
        success = await login.login(progress_callback=progress)

        if not success:
            print('❌ 로그인 실패 — 수동으로 로그인 후 Enter를 눌러주세요.')
            input('>> 로그인 완료 후 Enter: ')

        # 메뉴 이동 (업로드 없이)
        print('\n=== 간이지급명세서 메뉴 이동 ===')
        uploader = HometaxUploader(page)

        print('[1] 메인 페이지 이동 후 [지급명세·자료·공익법인] → [직접작성 제출]...')
        await page.goto(uploader.MAIN_URL, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        await uploader._navigate_to_direct_submit()

        print('[2] 거주자의 사업소득 선택 및 일괄등록 클릭...')
        await uploader._select_income_type()

        print('\n현재 URL:', page.url)
        print('화면을 확인하세요. 60초 후 브라우저를 닫습니다.')
        await page.wait_for_timeout(60000)
        await browser.close()


async def test_full(excel_path: str):
    """전체 파이프라인 테스트"""
    from rpa.rpa_runner import RPARunner

    print(f'\n=== 전체 RPA 테스트 ===')
    print(f'엑셀 파일: {excel_path}\n')

    runner = RPARunner(
        auth_method='certificate',
        excel_path=excel_path,
    )
    runner.set_progress_callback(progress)

    result = await runner.run()

    print(f'\n결과: {"성공" if result["success"] else "실패"}')
    print(f'메시지: {result["message"]}')


async def test_inspect():
    """현재 페이지 셀렉터 탐색 (디버그용)"""
    from playwright.async_api import async_playwright

    print('\n=== 홈택스 셀렉터 탐색 모드 ===')
    print('홈택스에 접속하여 페이지 구조를 분석합니다.\n')

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=100)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900}, locale='ko-KR'
        )
        page = await context.new_page()
        await page.goto('https://hometax.go.kr', wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)

        # 메인 페이지 요소 탐색
        print('=== 메인 페이지 탐색 ===')
        elements = await page.evaluate('''() => {
            const results = [];
            const all = document.querySelectorAll('a, button, span, input, li');
            all.forEach(el => {
                const text = (el.innerText || el.value || '').trim().substring(0, 50);
                if (text && text.length > 1) {
                    results.push({
                        tag: el.tagName,
                        id: el.id || '',
                        class: el.className ? el.className.substring(0, 60) : '',
                        text: text,
                        href: el.href || '',
                    });
                }
            });
            return results.slice(0, 100);  // 상위 100개
        }''')

        for el in elements:
            tag = el['tag']
            eid = f' id="{el["id"]}"' if el['id'] else ''
            cls = f' class="{el["class"]}"' if el['class'] else ''
            text = el['text'].replace('\n', ' ')[:40]
            print(f'  <{tag}{eid}{cls}> {text}')

        print(f'\n총 {len(elements)}개 요소 발견')
        print('\n원하는 페이지로 이동 후 Enter를 누르면 해당 페이지도 분석합니다.')
        print('종료하려면 "quit"를 입력하세요.')

        while True:
            cmd = input('\n>> Enter/quit: ').strip()
            if cmd.lower() == 'quit':
                break

            elements = await page.evaluate('''() => {
                const results = [];
                const all = document.querySelectorAll('a, button, span, input, li, label, div[onclick]');
                all.forEach(el => {
                    const text = (el.innerText || el.value || '').trim().substring(0, 50);
                    if (text && text.length > 1) {
                        results.push({
                            tag: el.tagName,
                            id: el.id || '',
                            class: el.className ? el.className.substring(0, 60) : '',
                            text: text,
                        });
                    }
                });
                return results.slice(0, 100);
            }''')

            print(f'\n현재 URL: {page.url}')
            for el in elements:
                tag = el['tag']
                eid = f' id="{el["id"]}"' if el['id'] else ''
                cls = f' class="{el["class"]}"' if el['class'] else ''
                text = el['text'].replace('\n', ' ')[:40]
                print(f'  <{tag}{eid}{cls}> {text}')

        await browser.close()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == 'login':
        asyncio.run(test_login())
    elif cmd == 'navigate':
        asyncio.run(test_navigate())
    elif cmd == 'full':
        if len(sys.argv) < 3:
            print('사용법: python test_rpa.py full <엑셀파일경로>')
            return
        asyncio.run(test_full(sys.argv[2]))
    elif cmd == 'inspect':
        asyncio.run(test_inspect())
    else:
        print(f'알 수 없는 명령: {cmd}')
        print(__doc__)


if __name__ == '__main__':
    main()
