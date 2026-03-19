"""홈택스 로그인 페이지 열기 — F12 확인용 (10분 대기)"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=300,
                                           args=['--start-maximized'])
        ctx = await browser.new_context(viewport={'width': 1280, 'height': 900},
                                         locale='ko-KR')
        page = await ctx.new_page()

        print('홈택스 접속 중...')
        await page.goto('https://hometax.go.kr',
                        wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(4000)

        # 로그인 페이지 이동
        print('로그인 페이지로 이동...')
        try:
            btn = page.locator('#mf_wfHeader_group1503')
            if await btn.is_visible(timeout=5000):
                await btn.click()
        except Exception:
            pass

        await page.wait_for_timeout(3000)
        print(f'현재 URL: {page.url}')
        print()
        print('='*50)
        print('브라우저가 열렸습니다!')
        print('F12를 눌러 아래 요소의 id를 확인해주세요:')
        print()
        print('  1. "공동·금융인증서" 탭 → id=?')
        print('  2. "간편인증" 탭 → id=?')
        print('  3. 로그인 실행 버튼 → id=?')
        print()
        print('10분 후 자동으로 닫힙니다.')
        print('='*50)

        await page.wait_for_timeout(600000)
        await browser.close()

asyncio.run(main())
