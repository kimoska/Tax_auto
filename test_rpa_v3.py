"""3차 테스트: hover + JS click으로 GNB 메뉴 이동 검증"""
import asyncio, json, os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)

async def run():
    from playwright.async_api import async_playwright
    results = []
    def log(name, ok, detail=''):
        print(f'{"✅" if ok else "❌"} {name}: {detail}')
        results.append({'step': name, 'ok': ok, 'detail': detail})

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=300)
        page = await (await browser.new_context(
            viewport={'width': 1280, 'height': 900}, locale='ko-KR')).new_page()

        # 1. 접속
        await page.goto('https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml',
                        wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(4000)
        log('홈택스 접속', True, page.url)

        # 2. GNB hover → 직접작성 제출 클릭
        method_used = ''
        success = False

        # 방법 1: hover
        try:
            parent = page.locator('#mf_wfHeader_hdGroup918')
            await parent.hover(timeout=5000)
            await page.wait_for_timeout(1500)
            direct = page.locator('#menuAtag_4401100000')
            if await direct.is_visible(timeout=3000):
                await direct.click()
                await page.wait_for_timeout(3000)
                method_used = 'hover→click'
                success = True
        except Exception as e:
            print(f'  hover 실패: {e}')

        # 방법 2: JS click
        if not success:
            try:
                result = await page.evaluate('''() => {
                    const el = document.getElementById('menuAtag_4401100000');
                    if (el) { el.click(); return 'clicked'; }
                    return 'not found';
                }''')
                await page.wait_for_timeout(3000)
                if result == 'clicked':
                    method_used = 'JS click'
                    success = True
                else:
                    print(f'  JS click: {result}')
            except Exception as e:
                print(f'  JS click 실패: {e}')

        # 방법 3: force click
        if not success:
            try:
                await page.locator('#menuAtag_4401100000').click(force=True, timeout=5000)
                await page.wait_for_timeout(3000)
                method_used = 'force click'
                success = True
            except Exception as e:
                print(f'  force click 실패: {e}')

        log('GNB → 직접작성 제출', success, f'방법: {method_used}, URL: {page.url}')

        # 3. 현재 화면 분석
        await page.wait_for_timeout(2000)
        try:
            body = await page.evaluate('() => document.body.innerText.substring(0, 300)')
            log('이동 후 화면', True, body[:100].replace('\n', ' '))

            # 보이는 요소
            els = await page.evaluate('''() => {
                const r = [];
                document.querySelectorAll('a, button, span, input, select, label').forEach(el => {
                    const t = (el.innerText||el.value||'').trim();
                    const b = el.getBoundingClientRect();
                    if (t.length > 0 && b.width > 0 && b.height > 0 && b.top > 0 && b.top < 900)
                        r.push({tag:el.tagName, id:el.id||'', text:t.substring(0,50)});
                });
                return r.slice(0,30);
            }''')
            print(f'\n  보이는 요소 ({len(els)}개):')
            for e in els:
                eid = f' id={e["id"]}' if e['id'] else ''
                print(f'    <{e["tag"]}{eid}> {e["text"][:40]}')
        except Exception as e:
            log('화면 분석', False, str(e)[:60])

        print(f'\n최종 URL: {page.url}')
        print('10초 후 닫기...')
        await page.wait_for_timeout(10000)
        await browser.close()

    with open(os.path.join(BASE_DIR, 'rpa_v3_result.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    print('=== 3차 검증: GNB hover + JS click ===\n')
    asyncio.run(run())
