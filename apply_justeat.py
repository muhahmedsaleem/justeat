import os
import re
import asyncio
from playwright.async_api import async_playwright
import requests

# Secrets / Config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TARGET_CITY = "Pisa"
FIRST_NAME = os.environ.get("FIRST_NAME", "Muhammad Ahmed")
LAST_NAME = os.environ.get("LAST_NAME", "Saleem")
EMAIL = os.environ.get("EMAIL", "ahmedmughal919530@gmail.com")
PHONE = os.environ.get("PHONE", "3784366484")
INVITE_CODE = os.environ.get("INVITE_CODE", "1484852")

# UPDATED URL: Links directly to Pisa
TARGET_URL = "https://www.justeat.it/rider/pisa?utm_source=RAF&utm_medium=RAFprogram&utm_campaign=Drivers&utm_term=RAF_1.0_DE&utm_content=blank&raf_id=9aab402d659e73d42cb6793599d61fb3"

def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[Telegram Not Configured] {message}")
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

        print(f"Navigating to {TARGET_URL}...")
        await page.goto(TARGET_URL, wait_until="networkidle")

        # --- NEW: Aggressively remove cookie banners from the page ---
        try:
            await page.evaluate("""() => {
                document.querySelectorAll('#pie_cookie_bar, pie-cookie-banner, #onetrust-consent-sdk').forEach(el => el.remove());
            }""")
        except Exception:
            pass

        # --- STEP 1: Select City & Apply ---
        print("Checking city selection...")
        try:
            city_dropdown = page.locator("button:not([disabled]):visible, div[role='button']:visible").filter(has_text=re.compile(r"Pisa|Seleziona", re.I)).first
            if await city_dropdown.is_visible(timeout=5000):
                await city_dropdown.click(force=True) # Forced click bypasses overlays
                await page.wait_for_timeout(1000)

                pisa_option = page.locator(f"text={TARGET_CITY}:visible").first
                if await pisa_option.is_visible():
                    await pisa_option.click(force=True)
                    await page.wait_for_timeout(1000)
        except Exception:
            print("City dropdown interaction skipped (likely already selected by URL).")

        # Click 'Candidati ora'
        print("Clicking Apply button...")
        apply_btn = page.locator("button:has-text('Candidati ora'):not([disabled]):visible, a:has-text('Candidati ora'):visible").first
        await apply_btn.wait_for(state="visible", timeout=10000)
        await apply_btn.click(force=True) # Forced click bypasses overlays
        await page.wait_for_load_state("networkidle")

        # --- STEP 2: Requirements checklist ---
        print("Passing Step 2...")
        proceed_btn = page.locator("button:has-text('Procedi')").first
        await proceed_btn.wait_for(state="visible", timeout=10000)
        await proceed_btn.click(force=True)
        await page.wait_for_load_state("networkidle")

        # --- STEP 3: Personal details ---
        print("Filling personal details...")
        await page.locator("input[name*='name'], input[placeholder*='Nome'], label:has-text('Nome') + input, input").nth(0).fill(FIRST_NAME)
        await page.locator("input[name*='surname'], input[name*='cognome'], label:has-text('Cognome') + input, input").nth(1).fill(LAST_NAME)
        await page.locator("input[type='email'], input[name*='email']").first.fill(EMAIL)
        await page.locator("input[type='tel'], input[name*='phone'], input[name*='telefono']").first.fill(PHONE)

        # Checkboxes
        checkboxes = page.locator("input[type='checkbox']")
        checkbox_count = await checkboxes.count()
        for i in range(checkbox_count):
            if not await checkboxes.nth(i).is_checked():
                await checkboxes.nth(i).check(force=True)

        # WhatsApp option: click 'Sì'
        si_whatsapp = page.locator("button:has-text('Sì'), div[role='button']:has-text('Sì')").first
        if await si_whatsapp.is_visible():
            await si_whatsapp.click(force=True)

        await page.locator("button:has-text('Procedi')").first.click(force=True)
        await page.wait_for_load_state("networkidle")

        # --- STEP 3B: Invite code ---
        print("Handling referral code...")
        si_invite = page.locator("button:has-text('Sì'), div[role='button']:has-text('Sì')").first
        if await si_invite.is_visible():
            await si_invite.click(force=True)
            invite_input = page.locator("input[name*='code'], input[placeholder*='invito'], input[type='text']").first
            await invite_input.fill(INVITE_CODE)

            ref_check = page.locator("input[type='checkbox']").first
            if await ref_check.is_visible() and not await ref_check.is_checked():
                await ref_check.check(force=True)

            await page.locator("button:has-text('Procedi')").first.click(force=True)
            await page.wait_for_load_state("networkidle")

        # --- STEP 4: Age verification ---
        print("Confirming age...")
        si_age = page.locator("button:has-text('Sì'), div[role='button']:has-text('Sì')").first
        await si_age.wait_for(state="visible", timeout=10000)
        await si_age.click(force=True)
        await page.locator("button:has-text('Procedi')").first.click(force=True)
        await page.wait_for_load_state("networkidle")

        # --- STEP 4B: Shift preference ---
        print("Selecting shift...")
        dinner_shift = page.locator("text='Orario di cena, sia in settimana che nel weekend'").first
        await dinner_shift.wait_for(state="visible", timeout=10000)
        await dinner_shift.click(force=True)
        await page.locator("button:has-text('Procedi')").first.click(force=True)
        await page.wait_for_load_state("networkidle")

        # --- STEP 4C: Vehicle Selection ---
        print("Checking vehicle selection...")
        await page.wait_for_timeout(2000)

        # Look for Electric Bike / E-Bike options
        ebike_option = page.locator("text=/e-bike|bici elettrica|electric bike|bicicletta elettrica/i").first
        
        if await ebike_option.is_visible():
            print("⚡ Electric bike option FOUND! Selecting it...")
            await ebike_option.click(force=True)
            await page.wait_for_timeout(1000)
            
            await page.locator("button:has-text('Procedi')").first.click(force=True)
            
            send_telegram(
                f"🎉 *Just Eat Pisa Alert!*\n\n"
                f"Electric Bike was found and selected for {TARGET_CITY}!\n"
                f"Check your application status here: {TARGET_URL}"
            )
        else:
            print("Electric bike is currently not listed among the available vehicles.")
            send_telegram(
                f"⚠️ *Just Eat Alert ({TARGET_CITY})*\n\n"
                f"Pisa application reached Step 4, but *Electric Bike* is not available right now."
            )

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())