from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def get_page_metrics(page):
    return page.evaluate("""
    () => ({
        viewportWidth: window.innerWidth,
        viewportHeight: window.innerHeight,
        docElScrollHeight: document.documentElement ? document.documentElement.scrollHeight : 0,
        bodyScrollHeight: document.body ? document.body.scrollHeight : 0,
        scrollingElementScrollHeight: document.scrollingElement ? document.scrollingElement.scrollHeight : 0
    })
    """)


def disable_animations(page):
    page.add_style_tag(content="""
        *,
        *::before,
        *::after {
            animation-duration: 0s !important;
            animation-delay: 0s !important;
            transition-duration: 0s !important;
            scroll-behavior: auto !important;
            caret-color: transparent !important;
        }
    """)


def make_images_eager(page):
    page.evaluate("""
    () => {
        for (const img of document.images) {
            img.loading = 'eager';
            img.decoding = 'sync';
        }
    }
    """)


def auto_scroll_page(page, step=700, delay=150):
    page.evaluate("""
    async ({ step, delay }) => {
        await new Promise(resolve => {
            let lastScrollY = -1;
            let stableCount = 0;

            const timer = setInterval(() => {
                window.scrollBy(0, step);

                const scrollY = window.scrollY;
                const viewportHeight = window.innerHeight;
                const totalHeight = document.scrollingElement
                    ? document.scrollingElement.scrollHeight
                    : document.documentElement.scrollHeight;

                if (scrollY === lastScrollY) {
                    stableCount++;
                } else {
                    stableCount = 0;
                }
                lastScrollY = scrollY;

                if (scrollY + viewportHeight >= totalHeight - 5 && stableCount >= 2) {
                    clearInterval(timer);
                    setTimeout(resolve, delay);
                }
            }, delay);
        });
    }
    """, {"step": step, "delay": delay})


def auto_scroll_element(page, selector, step=700, delay=150):
    page.evaluate("""
    async ({ selector, step, delay }) => {
        const el = document.querySelector(selector);
        if (!el) return false;

        await new Promise(resolve => {
            let lastScrollTop = -1;
            let stableCount = 0;

            const timer = setInterval(() => {
                el.scrollBy(0, step);

                if (el.scrollTop === lastScrollTop) {
                    stableCount++;
                } else {
                    stableCount = 0;
                }
                lastScrollTop = el.scrollTop;

                if (el.scrollTop + el.clientHeight >= el.scrollHeight - 5 && stableCount >= 2) {
                    clearInterval(timer);
                    setTimeout(resolve, delay);
                }
            }, delay);
        });

        return true;
    }
    """, {"selector": selector, "step": step, "delay": delay})


def wait_for_images(page, timeout=30000):
    try:
        page.wait_for_function("""
        () => {
            const imgs = Array.from(document.images);
            return imgs.every(img => img.complete);
        }
        """, timeout=timeout)
    except PlaywrightTimeoutError:
        print("Některé obrázky se asi nestihly načíst, pokračuji dál.")


def mark_best_scroll_container(page):
    """
    Najde nejpravděpodobnější hlavní scrollovací kontejner,
    pokud root dokument není vysoký.
    Označí ho atributem data-pw-scroll-root="1".
    """
    return page.evaluate("""
    () => {
        const old = document.querySelector('[data-pw-scroll-root="1"]');
        if (old) old.removeAttribute('data-pw-scroll-root');

        const vw = window.innerWidth;
        const vh = window.innerHeight;

        function isVisible(el) {
            const s = getComputedStyle(el);
            const r = el.getBoundingClientRect();
            return (
                s.display !== 'none' &&
                s.visibility !== 'hidden' &&
                parseFloat(s.opacity || '1') > 0 &&
                r.width > 0 &&
                r.height > 0
            );
        }

        function isScrollLike(el) {
            const s = getComputedStyle(el);
            return ['auto', 'scroll', 'overlay'].includes(s.overflowY) ||
                   ['auto', 'scroll', 'overlay'].includes(s.overflow);
        }

        let bestEl = null;
        let bestInfo = null;
        let bestScore = -1;

        for (const el of document.body.querySelectorAll('*')) {
            if (!isVisible(el)) continue;

            const rect = el.getBoundingClientRect();

            // ignoruj malé a úzké elementy
            if (rect.width < vw * 0.35) continue;
            if (rect.height < 120) continue;

            const scrollHeight = el.scrollHeight;
            const clientHeight = el.clientHeight;

            // musí být významně vyšší než je viditelná část
            if (scrollHeight < Math.max(clientHeight + 250, vh * 1.5)) continue;

            // musí to aspoň trochu vypadat jako scrollovací kontejnér
            if (!isScrollLike(el) && scrollHeight <= clientHeight + 250) continue;

            // preference: široký, středový, vysoký
            const centerX = rect.left + rect.width / 2;
            const centrality = 1 - Math.min(1, Math.abs(centerX - vw / 2) / (vw / 2));
            const widthScore = rect.width / vw;
            const tallScore = scrollHeight / vh;

            const score = tallScore * (0.6 + centrality) * (0.6 + widthScore);

            if (score > bestScore) {
                bestScore = score;
                bestEl = el;
                bestInfo = {
                    tag: el.tagName,
                    id: el.id || "",
                    className: typeof el.className === "string" ? el.className : "",
                    rectWidth: Math.round(rect.width),
                    rectHeight: Math.round(rect.height),
                    clientHeight: clientHeight,
                    scrollHeight: scrollHeight,
                    score: score
                };
            }
        }

        if (!bestEl) return null;

        bestEl.setAttribute('data-pw-scroll-root', '1');
        return bestInfo;
    }
    """)


def expand_marked_container(page):
    """
    Rozbalí označený scrollovací kontejner i jeho předky,
    aby se obsah promítl do normální výšky stránky.
    """
    return page.evaluate("""
    () => {
        const target = document.querySelector('[data-pw-scroll-root="1"]');
        if (!target) return false;

        let el = target;
        while (el && el !== document.documentElement) {
            el.style.overflow = 'visible';
            el.style.overflowY = 'visible';
            el.style.maxHeight = 'none';
            el.style.height = 'auto';
            el = el.parentElement;
        }

        document.documentElement.style.overflow = 'visible';
        document.documentElement.style.height = 'auto';
        document.documentElement.style.maxHeight = 'none';

        document.body.style.overflow = 'visible';
        document.body.style.height = 'auto';
        document.body.style.maxHeight = 'none';

        return true;
    }
    """)


def capture_smart_full_page(url, output_name="screenshot.png"):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1
        )
        page = context.new_page()

        print(f"Načítám: {url}")
        page.goto(url, wait_until="load", timeout=60000)
        page.wait_for_timeout(2000)

        disable_animations(page)
        make_images_eager(page)

        # 1) normální scroll celé stránky kvůli lazy-loadu
        auto_scroll_page(page)
        wait_for_images(page)

        metrics = get_page_metrics(page)
        print("Původní metrics:", metrics)

        viewport_h = metrics["viewportHeight"]
        root_h = max(
            metrics["docElScrollHeight"],
            metrics["bodyScrollHeight"],
            metrics["scrollingElementScrollHeight"]
        )

        # 2) Pokud root dokument není vysoký, zkus najít vnitřní scrollovací kontejner
        if root_h <= viewport_h * 1.2:
            print("Root dokument je skoro stejně vysoký jako viewport -> hledám vnitřní scrollovací kontejner...")

            info = mark_best_scroll_container(page)
            print("Nalezený kandidát:", info)

            if info:
                # nejdřív ho projeď, aby se načetl lazy obsah uvnitř něj
                auto_scroll_element(page, '[data-pw-scroll-root="1"]')
                page.wait_for_timeout(800)

                # pak ho rozbal do normální stránky
                expanded = expand_marked_container(page)
                print("Rozbalení kontejneru:", expanded)

                page.wait_for_timeout(1500)

                # znovu projeď root stránku, protože po rozbalení už může být opravdu dlouhá
                auto_scroll_page(page)
                wait_for_images(page)

                metrics_after = get_page_metrics(page)
                print("Metrics po rozbalení:", metrics_after)
            else:
                print("Žádný vhodný vnitřní scrollovací kontejner jsem nenašel.")

        # zpět nahoru
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(800)

        # finální screenshot
        page.screenshot(
            path=output_name,
            full_page=True,
            animations="disabled"
        )

        print(f"Hotovo, uložen screenshot: {output_name}")
        browser.close()


if __name__ == "__main__":
    capture_smart_full_page(
        "https://oiwiki.swpelc.eu/doku.php?id=statnice:bakalar:b4b35osy",
        "oiwiki_full_osy.png"
    )