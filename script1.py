from playwright.sync_api import sync_playwright

def capture_full_page(url, output_name="screenshot.png"):
    with sync_playwright() as p:
        # Spustí prohlížeč (headless=True znamená, že neuvidíte okno)
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Nastavení rozlišení (šířka 1280px, výška se přizpůsobí)
        page.set_viewport_size({"width": 1280, "height": 800})
        
        print(f"Načítám stránku: {url}")
        page.goto(url, wait_until="networkidle") # Počká, až ustane síťová aktivita
        
        # Samotný screenshot celé plochy
        page.screenshot(path=output_name, full_page=True)
        
        print(f"Hotovo! Screenshot uložen jako {output_name}")
        browser.close()

# Tady zadejte svou adresu
capture_full_page("https://www.to-das.cz/cermat-prijimacky-nanecisto-2026-vysledky-a-zadani/")