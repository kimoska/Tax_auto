"""
AutoTax — RPA 2차 검증 테스트
업데이트된 셀렉터로 GNB 메뉴 클릭까지 테스트 (로그인 불필요 구간)
"""
import asyncio
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


async def run():
    from playwright.async_api import async_playwright

    results = []

    def log(name, ok, detail=''):
        icon = '✅' if ok else '❌'
        print(f'{icon} {name}: {detail}')
        results.append({'step': name, 'ok': ok, 'detail': detail})

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=500)
        ctx = await browser.new_context(
            viewport={'width': 1280, 'height': 900}, locale='ko-KR')
        page = await ctx.new_page()

        # 1. 홈택스 접속
        await page.goto('https://hometax.go.kr', wait_until='domcontentloaded',
                        timeout=30000)
        await page.wait_for_timeout(4000)
        log('홈택스 접속', True, page.url)

        # 2. GNB "지급명세·자료·공익법인" 클릭 (검증된 ID)
        try:
            gnb = page.locator('#mf_wfHeader_wq_uuid_438')
            visible = await gnb.is_visible(timeout=5000)
            if visible:
                await gnb.click()
                await page.wait_for_timeout(2000)
                log('GNB 지급명세 클릭', True, '#mf_wfHeader_wq_uuid_438')
            else:
                log('GNB 지급명세 클릭', False, '보이지 않음')
        except Exception as e:
            log('GNB 지급명세 클릭', False, str(e)[:60])

        # 3. "직접작성 제출" 클릭 (검증된 ID)
        try:
            direct = page.locator('#menuAtag_4401100000')
            visible = await direct.is_visible(timeout=5000)
            if visible:
                await direct.click()
                await page.wait_for_timeout(3000)
                log('직접작성 제출 클릭', True, '#menuAtag_4401100000')
            else:
                log('직접작성 제출 클릭', False, '보이지 않음')
        except Exception as e:
            log('직접작성 제출 클릭', False, str(e)[:60])

        # 4. 현재 페이지 분석 (로그인 필요 화면일 수 있음)
        try:
            await page.wait_for_timeout(3000)
            page_text = await page.evaluate('() => document.body.innerText.substring(0, 500)')
            log('페이지 상태 확인', True, page_text[:100].replace('\n', ' '))

            # 로그인 필요 여부 확인
            if '로그인' in page_text and ('필요' in page_text or '후' in page_text):
                log('로그인 필요 확인', True, '로그인 후 접근 가능한 페이지')
            elif '소득자료' in page_text or '간이지급' in page_text:
                log('소득자료 선택 화면', True, '로그인 없이 진입됨')

            # 보이는 요소 수집
            visible_els = await page.evaluate('''() => {
                const results = [];
                const all = document.querySelectorAll('a, button, span, input, select');
                all.forEach(el => {
                    const text = (el.innerText || el.value || '').trim();
                    const rect = el.getBoundingClientRect();
                    if (text.length > 0 && rect.width > 0 && rect.height > 0
                        && rect.top > 0 && rect.top < 900) {
                        results.push({
                            tag: el.tagName, id: el.id || '',
                            text: text.substring(0, 50),
                        });
                    }
                });
                return results.slice(0, 50);
            }''')
            print(f'\n  현재 화면 보이는 요소 ({len(visible_els)}개):')
            for el in visible_els:
                eid = f' id={el["id"]}' if el['id'] else ''
                print(f'    <{el["tag"]}{eid}> {el["text"][:40]}')

        except Exception as e:
            log('페이지 분석', False, str(e)[:60])

        print(f'\n현재 URL: {page.url}')
        print('15초 후 브라우저 닫기...')
        await page.wait_for_timeout(15000)
        await browser.close()

    # 결과 저장
    with open(os.path.join(BASE_DIR, 'rpa_verify_result.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print('\n=== 요약 ===')
    for r in results:
        print(f'{"✅" if r["ok"] else "❌"} {r["step"]}: {r["detail"][:60]}')


if __name__ == '__main__':
    print('=== RPA 셀렉터 2차 검증 ===\n')
    asyncio.run(run())
