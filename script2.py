from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time


def auto_scroll(page, step=700, delay=150):
    """
    Pomalu projede stránku dolů, aby se načetly lazy-load obrázky.
    """
    page.evaluate(
        """
        async ({ step, delay }) => {
            await new Promise(resolve => {
                let lastScrollHeight = 0;

                const timer = setInterval(() => {
                    window.scrollBy(0, step);

                    const scrollTop = window.scrollY;
                    const scrollHeight = document.documentElement.scrollHeight;
                    const viewportHeight = window.innerHeight;

                    if (scrollHeight === lastScrollHeight &&
                        scrollTop + viewportHeight >= scrollHeight - 5) {
                        clearInterval(timer);
                        setTimeout(resolve, delay);
                    }

                    lastScrollHeight = scrollHeight;
                }, delay);
            });
        }
        """,
        {"step": step, "delay": delay}
    )


def wait_for_images(page, timeout=30000):
    """
    Počká, až se načtou obrázky, které jsou v DOM.
    Nezastaví se navždy kvůli rozbitým obrázkům.
    """
    try:
        page.wait_for_function(
            """
            () => {
                const images = Array.from(document.images);
                return images.every(img => img.complete);
            }
            """,
            timeout=timeout
        )
    except PlaywrightTimeoutError:
        unloaded = page.evaluate(
            """
            () => Array.from(document.images)
                .filter(img => !img.complete || img.naturalWidth === 0)
                .map(img => img.currentSrc || img.src)
            """
        )

        print("Některé obrázky se nestihly nebo nepodařilo načíst:")
        for src in unloaded:
            print(" -", src)


def capture_full_page(url, output_name="screenshot.png"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1
        )

        page = context.new_page()

        print(f"Načítám stránku: {url}")

        page.goto(url, wait_until="load", timeout=60000)

        # Vypnutí animací a plynulého scrollování, aby se screenshot nerozmazal/neposunul
        page.add_style_tag(content="""
            *,
            *::before,
            *::after {
                animation-duration: 0s !important;
                animation-delay: 0s !important;
                transition-duration: 0s !important;
                scroll-behavior: auto !important;
            }
        """)

        # Donutí běžné img prvky nenačítat se líně
        page.evaluate("""
            () => {
                for (const img of document.images) {
                    img.loading = 'eager';
                }
            }
        """)

        # Počkat na fonty, pokud je prohlížeč podporuje
        try:
            page.evaluate("() => document.fonts && document.fonts.ready")
        except Exception:
            pass

        print("Scrolluji stránku, aby se načetly lazy obrázky...")
        auto_scroll(page)

        # Krátce nahoru a dolů, někdy to pomůže s IntersectionObserver lazy-loadem
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)
        auto_scroll(page)

        print("Čekám na obrázky...")
        wait_for_images(page)

        # Vrátit na začátek, aby screenshot začínal nahoře
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        print("Ukládám screenshot...")
        page.screenshot(
            path=output_name,
            full_page=True,
            animations="disabled"
        )

        print(f"Hotovo! Screenshot uložen jako {output_name}")

        browser.close()


capture_full_page(
    "https://www.to-das.cz/cermat-prijimacky-nanecisto-2026-vysledky-a-zadani/",
    "to-das-screenshot.png"
)