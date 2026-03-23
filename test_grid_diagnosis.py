"""
홈택스 상세내역 그리드 구조 진단 스크립트.
실제 브라우저에서 그리드의 HTML 구조, 셀 ID, 버튼 위치를 파악합니다.
"""
import asyncio
import logging
import json

from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger(__name__)


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=300,
            args=['--start-maximized',
                  '--disable-blink-features=AutomationControlled',
                  '--disable-features=BlockInsecurePrivateNetworkRequests'],
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ko-KR',
            timezone_id='Asia/Seoul',
        )
        page = await context.new_page()

        # 1. 홈택스 메인 이동
        logger.info("=== 홈택스 메인 페이지로 이동 ===")
        await page.goto(
            'https://hometax.go.kr/websquare/websquare.html?w2xPath=/ui/pp/index_pp.xml',
            wait_until='domcontentloaded', timeout=30000
        )
        
        # 2. 수동 로그인 대기 (60초 — 사용자가 직접 로그인)
        logger.info("=" * 60)
        logger.info("⏳ 로그인을 해주세요! 60초 대기...")
        logger.info("   로그인 후 [상세내역 작성하기]까지 직접 진행해주세요.")
        logger.info("   목록이 보이면 아무 키나 누르세요.")
        logger.info("=" * 60)
        await page.wait_for_timeout(60000)

        # 3. 그리드 HTML 구조 분석
        logger.info("\n=== 🔍 그리드 구조 분석 시작 ===\n")
        
        # 3-1: gridList01 관련 요소 모두 찾기
        result = await page.evaluate('''() => {
            const output = {};
            
            // 1. gridList01 관련 셀 전체 ID 수집
            const allElements = document.querySelectorAll('[id*="gridList01_cell"]');
            output.gridCellCount = allElements.length;
            output.gridCellIds = Array.from(allElements).slice(0, 30).map(el => ({
                id: el.id,
                tag: el.tagName,
                text: el.textContent.trim().substring(0, 50),
                html: el.innerHTML.substring(0, 200)
            }));
            
            // 2. 수정 버튼 찾기 (여러 방법)
            const editButtons = [];
            
            // 방법 A: data-value="수정" 셀
            const modCells = document.querySelectorAll('[data-value="수정"]');
            modCells.forEach(cell => {
                const btn = cell.querySelector('button');
                editButtons.push({
                    method: 'data-value',
                    cellId: cell.id,
                    cellTag: cell.tagName,
                    hasButton: !!btn,
                    buttonText: btn ? btn.textContent.trim() : '',
                    visible: cell.offsetWidth > 0 && cell.offsetHeight > 0
                });
            });
            
            // 방법 B: data-col_id="modifyGrdData" 
            const modGrdCells = document.querySelectorAll('[data-col_id="modifyGrdData"]');
            modGrdCells.forEach(cell => {
                const btn = cell.querySelector('button');
                editButtons.push({
                    method: 'data-col_id',
                    cellId: cell.id,
                    cellTag: cell.tagName,
                    hasButton: !!btn,
                    buttonText: btn ? btn.textContent.trim() : '',
                    visible: cell.offsetWidth > 0 && cell.offsetHeight > 0
                });
            });
            
            // 방법 C: 일반 button:수정 찾기
            const allButtons = document.querySelectorAll('button');
            let editBtnCount = 0;
            allButtons.forEach(btn => {
                if (btn.textContent.trim() === '수정' && editBtnCount < 5) {
                    editButtons.push({
                        method: 'button-text',
                        parentId: btn.parentElement?.id || '',
                        grandparentId: btn.parentElement?.parentElement?.id || '',
                        visible: btn.offsetWidth > 0 && btn.offsetHeight > 0
                    });
                    editBtnCount++;
                }
            });
            
            output.editButtons = editButtons;
            
            // 3. 컬럼 구조 파악 (첫 행의 모든 셀)
            const firstRowCells = [];
            let colIdx = 0;
            while (true) {
                const prefix = 'mf_txppWframe_wfDetailBrkd_gridList01_cell';
                const cell = document.getElementById(prefix + '_0_' + colIdx);
                if (!cell) break;
                firstRowCells.push({
                    colIndex: colIdx,
                    id: cell.id,
                    text: cell.textContent.trim().substring(0, 30),
                    dataValue: cell.getAttribute('data-value') || '',
                    dataColId: cell.getAttribute('data-col_id') || '',
                    hasButton: !!cell.querySelector('button')
                });
                colIdx++;
            }
            output.firstRowCells = firstRowCells;
            
            // 4. 페이지 내 주요 폼 요소 확인
            const formIds = [
                'mf_txppWframe_wfDetailBrkd_edtTotaPymnAmt',
                'mf_txppWframe_wfDetailBrkd_btnAddRow',
                'mf_txppWframe_wfDetailBrkd_pglNavi1_page_2',
            ];
            output.formElements = {};
            formIds.forEach(id => {
                const el = document.getElementById(id);
                output.formElements[id] = el ? {
                    exists: true,
                    visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 30),
                } : { exists: false };
            });
            
            return output;
        }''')

        # 결과 출력 및 저장
        output_path = 'grid_diagnosis.json'
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\n📊 전체 결과 → {output_path}")
        logger.info(f"\n그리드 셀 총 개수: {result.get('gridCellCount', 0)}")
        
        logger.info("\n--- 첫 번째 행 컬럼 구조 ---")
        for cell in result.get('firstRowCells', []):
            logger.info(f"  컬럼 {cell['colIndex']}: id={cell['id']}, "
                       f"text='{cell['text']}', data-col_id='{cell['dataColId']}', "
                       f"hasButton={cell['hasButton']}")
        
        edit_btns = result.get('editButtons', [])
        logger.info(f"\n--- 수정 버튼 탐색 결과 ({len(edit_btns)}개) ---")
        for btn in result.get('editButtons', []):
            logger.info(f"  {btn}")
        
        logger.info("\n--- 폼 요소 확인 ---")
        for fid, info in result.get('formElements', {}).items():
            logger.info(f"  {fid}: {info}")

        # 수정 버튼 실제 클릭 테스트 (첫 번째 행)
        logger.info("\n=== 🖱️ 수정 버튼 클릭 테스트 ===")
        
        # 테스트 1: data-value="수정" 첫 번째 셀의 button 클릭
        click_result = await page.evaluate('''() => {
            const cells = document.querySelectorAll('[data-value="수정"]');
            if (cells.length > 0) {
                const btn = cells[0].querySelector('button');
                if (btn) {
                    btn.click();
                    return 'clicked: ' + cells[0].id;
                }
                return 'no_button_in_cell: ' + cells[0].id;
            }
            return 'no_cells_found';
        }''')
        logger.info(f"JS 클릭 결과: {click_result}")
        
        await page.wait_for_timeout(3000)
        
        # 클릭 후 지급액 필드 확인
        pay_check = await page.evaluate('''() => {
            const el = document.getElementById('mf_txppWframe_wfDetailBrkd_edtTotaPymnAmt');
            if (el) {
                return {
                    exists: true,
                    visible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    value: el.value || '',
                    type: el.type
                };
            }
            return { exists: false };
        }''')
        logger.info(f"지급액 필드 상태: {pay_check}")
        
        logger.info("\n=== ✅ 진단 완료! 브라우저는 60초 후 닫힙니다 ===")
        await page.wait_for_timeout(60000)
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
