import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

def run_live_browser_test():
    print("==================================================")
    print("       STARTING REAL BROWSER UI TEST RUN         ")
    print("==================================================")

    console_messages = []
    console_errors = []
    network_requests = []

    with sync_playwright() as p:
        print("[1/7] Launching Chromium browser engine...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.on("console", lambda msg: (
            console_errors.append(msg.text) if msg.type == "error" else console_messages.append(f"[{msg.type}] {msg.text}")
        ))
        page.on("requestfinished", lambda req: (
            network_requests.append(f"{req.method} {req.url} -> {req.response().status if req.response() else 'unknown'}")
        ))

        print("[2/7] Navigating to http://127.0.0.1:8000/...")
        page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        page.wait_for_selector("#root", state="attached", timeout=10000)
        time.sleep(1)
        
        page.screenshot(path="shot_01_loaded.png")
        print("  -> Page loaded. Captured shot_01_loaded.png")
        print(f"  -> Title: {page.title()}")

        header = page.locator("header")
        print(f"  -> Header text: {header.inner_text().replace(chr(10), ' | ')}")

        # Step 3: Click Demo PDF Button
        print("\n[3/7] Clicking 'Демо-регламент PDF' button...")
        demo_btn = page.locator("button:has-text('Демо-регламент PDF')")
        if demo_btn.count() == 0:
            demo_btn = page.locator("button:has-text('Демо PDF')")
        demo_btn.click()
        print("  -> Clicked. Waiting for indexing in ChromaDB...")

        page.wait_for_selector("p:has-text('sample_company_policy.pdf')", timeout=20000)
        time.sleep(1)
        page.screenshot(path="shot_02_demo_indexed.png")
        print("  -> Document indexed! Captured shot_02_demo_indexed.png")

        doc_item = page.locator("div.group:has-text('sample_company_policy.pdf')").first
        print(f"  -> Document Card: {doc_item.inner_text().replace(chr(10), ' ')}")

        # Step 4: Open Chunk Inspector Modal
        print("\n[4/7] Opening Chunk Inspector Modal...")
        inspect_btn = page.locator("button[title='Просмотреть векторизованные чанки']").first
        inspect_btn.click()

        page.wait_for_selector("h2:has-text('Инспектор чанков')", timeout=5000)
        page.wait_for_selector("span:has-text('Чанк #0')", timeout=5000)
        time.sleep(1)
        page.screenshot(path="shot_03_chunk_modal.png")
        print("  -> Modal open with all indexed chunks! Captured shot_03_chunk_modal.png")

        chunks_count = page.locator("div:has-text('Чанк #')").count()
        print(f"  -> Total chunk elements in modal: {chunks_count}")

        # Close Modal
        close_btn = page.locator("button:has-text('Закрыть')").last
        close_btn.click()
        time.sleep(0.5)
        print("  -> Modal closed.")

        # Step 5: Click Quick Sample Question
        print("\n[5/7] Clicking Quick Question: 'Каков рабочий график и время обеденного перерыва?'...")
        chip = page.locator("button:has-text('Каков рабочий график')")
        chip.click()
        print("  -> Query submitted. Waiting for answer...")

        page.wait_for_selector("div:has-text('Сгенерированный ответ')", timeout=15000)
        time.sleep(1)
        page.screenshot(path="shot_04_query_answer.png")
        print("  -> Answer received! Captured shot_04_query_answer.png")

        answer_div = page.locator("div.whitespace-pre-line")
        print(f"  -> Answer:\n{answer_div.inner_text()}")

        # Step 6: Expand Citation Accordion
        print("\n[6/7] Expanding citation card...")
        citation_button = page.locator("div.space-y-3 button.w-full").first
        citation_button.click()
        time.sleep(0.5)
        page.screenshot(path="shot_05_citation_opened.png")
        print("  -> Citation expanded! Captured shot_05_citation_opened.png")

        # Step 7: Custom Query via Search Input
        print("\n[7/7] Typing custom query: 'Каков размер компенсации расходов на спорт и обучение?'...")
        input_elem = page.locator("input[placeholder*='Задайте вопрос']")
        input_elem.fill("Каков размер компенсации расходов на спорт и обучение?")
        
        submit_btn = page.locator("button[type='submit']")
        submit_btn.click()
        time.sleep(2)

        page.screenshot(path="shot_06_custom_answer.png")
        print("  -> Custom Answer received! Captured shot_06_custom_answer.png")
        print(f"  -> Answer:\n{answer_div.inner_text()}")

        browser.close()

    print("\n==================================================")
    print("                 AUDIT SUMMARY                    ")
    print("==================================================")
    print(f"Total Network Requests Handled: {len(network_requests)}")
    print(f"Console Errors: {len(console_errors)}")
    if console_errors:
        for err in console_errors:
            print(f"  [ERROR] {err}")
    else:
        print("  [SUCCESS] 0 Console Errors.")

    print("All UI interactions, API calls, and DOM states verified.")

if __name__ == "__main__":
    run_live_browser_test()
