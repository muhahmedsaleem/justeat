import os
import re
import asyncio
from playwright.async_api import async_playwright
import requests

# --- GITHUB SECRETS ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FIRST_NAME = os.environ.get("FIRST_NAME")
LAST_NAME = os.environ.get("LAST_NAME")
EMAIL = os.environ.get("EMAIL")
PHONE = os.environ.get("PHONE")
INVITE_CODE = os.environ.get("INVITE_CODE")

TARGET_CITY = "Pisa"
TARGET_URL = "https://www.justeat.it/rider/pisa?utm_source=RAF&utm_medium=RAFprogram&utm_campaign=Drivers&utm_term=RAF_1.0_DE&utm_content=blank&raf_id=9aab402d659e73d42cb6793599d61fb3"

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram Not Configured] Message not sent.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="it-IT"
        )
        page = await context.new_page()

        # Helper function to handle SPA slide animations
        async def smart_action(locator_str, text_to_fill=None, retries=8):
            for attempt in range(retries):
                elements = page.locator(locator_str)
                count = await elements.count()
                for i in range(count):
                    el = elements.nth(i)
                    if await el.is_visible():
                        box = await el.bounding_box()
                        if box and box['x'] >= 0 and box['x'] < 2000 and box['width'] > 0:
                            await el.scroll_into_view_if_needed()
                            if text_to_fill is not None:
                                await el.fill(text_to_fill)
                            else:
                                await el.click(force=True)
                            await page.wait_for_timeout(500)
                            return True
                await page.wait_for_timeout(1000)
            return False

        async def check_visible_checkboxes():
            checkboxes = page.locator("input[type='checkbox']")
            count = await checkboxes.count()
            for i in range(count):
                cb = checkboxes.nth(i)
                if await cb.is_visible():
                    box = await cb.bounding_box()
                    if box and box['x'] >= 0 and box['width'] > 0:
                        if not await cb.is_checked():
                            await cb.check(force=True)

        print(f"Navigating to {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="networkidle")

        print("Neutralizing cookie banners...")
        await page.wait_for_timeout(2000)
        try:
            accept_btn = page.locator("button:has-text('Accetta'), button:has-text('Accept'), [data-test-id='accept-all-cookies']").first
            if await accept_btn.is_visible(timeout=2000):
                await accept_btn.click(force=True)
        except Exception:
            pass

        await page.add_style_tag(content="""
            #pie_cookie_bar, pie-cookie-banner, .cookie-overlay, .modal__open, .cookie_bar, #onetrust-consent-sdk 
            { display: none !important; opacity: 0 !important; visibility: hidden !important; pointer-events: none !important; z-index: -99999 !important; }
        """)
        await page.wait_for_timeout(1000)

        # --- STEP 1: Select City & Apply ---
        print("Checking city selection...")
        await smart_action("button:has-text('Pisa'), div[role='button']:has-text('Pisa'), :text('Pisa')")
        
        print("Clicking Apply button...")
        await smart_action("button:has-text('Candidati ora'), a:has-text('Candidati ora')")
        await page.wait_for_timeout(2000)

        # --- STEP 2: Requirements checklist ---
        print("Passing Step 2...")
        await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
        await page.wait_for_timeout(2000)

        # --- STEP 3: Personal details ---
        print("Filling personal details...")
        await smart_action("input[name='firstName'], input[name='name'], input[placeholder='Nome'], label:has-text('Nome') + input", text_to_fill=FIRST_NAME)
        await smart_action("input[name='lastName'], input[name='surname'], input[name='cognome'], input[placeholder='Cognome'], label:has-text('Cognome') + input", text_to_fill=LAST_NAME)
        await smart_action("input[type='email'], input[name*='email']", text_to_fill=EMAIL)
        await smart_action("input[type='tel'], input[name*='phone'], input[name*='telefono']", text_to_fill=PHONE)

        print("Checking Terms & WhatsApp...")
        await check_visible_checkboxes()
        await smart_action("button:has-text('Sì'), div[role='button']:has-text('Sì')")
        
        print("Proceeding to Step 3B...")
        await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
        await page.wait_for_timeout(2500)

        # --- STEP 3B: Invite code ---
        print("Handling referral code...")
        await smart_action("button:has-text('Sì'), div[role='button']:has-text('Sì')")
        await smart_action("input[name*='code'], input[placeholder*='invito'], input[type='text']", text_to_fill=INVITE_CODE)
        await check_visible_checkboxes()
        
        print("Proceeding to Step 4...")
        await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
        await page.wait_for_timeout(2500)

        # --- STEP 4: Age verification ---
        print("Confirming age...")
        await smart_action("button:has-text('Sì'), div[role='button']:has-text('Sì')")
        await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
        await page.wait_for_timeout(2500)

        # --- STEP 4B: Shift preference ---
        print("Selecting shift...")
        await smart_action("text=\"Orario di cena, sia in settimana che nel weekend\"")
        await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
        await page.wait_for_timeout(2500)

        # --- STEP 4C: Vehicle Selection ---
        print("Checking vehicle selection...")
        found_ebike = await smart_action("text=/e-bike|bici elettrica|electric bike|bicicletta elettrica/i")
        
        if found_ebike:
            print("⚡ Electric bike option FOUND! Selecting it...")
            await smart_action("button:has-text('Procedi'), div[role='button']:has-text('Procedi')")
            send_telegram(
                f"🎉 *Just Eat Pisa Alert!*\n\n"
                f"Electric Bike option was found and selected for *{TARGET_CITY}*!\n\n"
                f"Link: {TARGET_URL}"
            )
        else:
            print("Electric bike is not available right now. Exiting silently...")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())