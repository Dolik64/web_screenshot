from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


URL = "https://oiwiki.swpelc.eu/doku.php?id=statnice:bakalar:b0b01pst"
OUTPUT_PDF = "oiwiki_b4b36pst.pdf"


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


def auto_scroll_page(page, step=700, delay=120):
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


def auto_scroll_element(page, selector, step=700, delay=120):
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
    Najde nejpravděpodobnější hlavní vnitřní scrollovací kontejner.
    """
    return page.evaluate("""
    () => {
        const old = document.querySelector('[data-pw-scroll-root="1"]');
        if (old) old.removeAttribute('data-pw-scroll-root');

        const vw = window.innerWidth;
        const vh = window.innerHeight;

        function getClassName(el) {
            if (typeof el.className === "string") return el.className;
            return "";
        }

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
            return (
                ['auto', 'scroll', 'overlay'].includes(s.overflowY) ||
                ['auto', 'scroll', 'overlay'].includes(s.overflow)
            );
        }

        function looksLikeSidebarOrMenu(el) {
            const text = (
                el.tagName + " " +
                (el.id || "") + " " +
                getClassName(el)
            ).toLowerCase();

            return (
                text.includes("sidebar") ||
                text.includes("nav") ||
                text.includes("menu") ||
                text.includes("toc") ||
                text.includes("breadcrumb") ||
                text.includes("header") ||
                text.includes("footer")
            );
        }

        let bestEl = null;
        let bestInfo = null;
        let bestScore = -1;

        for (const el of document.body.querySelectorAll('*')) {
            if (!isVisible(el)) continue;

            const rect = el.getBoundingClientRect();
            const scrollHeight = el.scrollHeight;
            const clientHeight = el.clientHeight;

            if (scrollHeight <= clientHeight + 250) continue;
            if (rect.width < vw * 0.30) continue;
            if (rect.height < 100) continue;

            const centerX = rect.left + rect.width / 2;
            const centrality = 1 - Math.min(1, Math.abs(centerX - vw / 2) / (vw / 2));
            const widthScore = rect.width / vw;
            const tallScore = scrollHeight / vh;
            const scrollBonus = isScrollLike(el) ? 2.0 : 1.0;
            const sidebarPenalty = looksLikeSidebarOrMenu(el) ? 0.25 : 1.0;

            const score =
                tallScore *
                (0.6 + centrality) *
                (0.6 + widthScore) *
                scrollBonus *
                sidebarPenalty;

            if (score > bestScore) {
                bestScore = score;
                bestEl = el;
                bestInfo = {
                    tag: el.tagName,
                    id: el.id || "",
                    className: getClassName(el),
                    rectWidth: Math.round(rect.width),
                    rectHeight: Math.round(rect.height),
                    clientHeight: clientHeight,
                    scrollHeight: scrollHeight,
                    overflowY: getComputedStyle(el).overflowY,
                    score: Math.round(score * 100) / 100
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
    Rozbalí nalezený scrollovací kontejner a jeho rodiče.
    """
    return page.evaluate("""
    () => {
        const target = document.querySelector('[data-pw-scroll-root="1"]');
        if (!target) return false;

        let el = target;

        while (el && el !== document.documentElement) {
            el.style.overflow = 'visible';
            el.style.overflowY = 'visible';
            el.style.overflowX = 'visible';
            el.style.maxHeight = 'none';
            el.style.height = 'auto';
            el.style.minHeight = '0';
            el.style.position = getComputedStyle(el).position === 'fixed' ? 'static' : el.style.position;

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


def prepare_page_for_full_export(page):
    disable_animations(page)
    make_images_eager(page)

    # První scroll kvůli lazy-load prvkům.
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

    # Když root dokument není vysoký, hledáme vnitřní scrollovací layout.
    if root_h <= viewport_h * 1.2:
        print("Root dokument je skoro stejně vysoký jako viewport -> hledám vnitřní scrollovací kontejner...")

        info = mark_best_scroll_container(page)
        print("Nalezený kandidát:", info)

        if info:
            auto_scroll_element(page, '[data-pw-scroll-root="1"]')
            page.wait_for_timeout(800)

            expanded = expand_marked_container(page)
            print("Rozbalení kontejneru:", expanded)

            page.wait_for_timeout(1500)

            auto_scroll_page(page)
            wait_for_images(page)

            metrics_after = get_page_metrics(page)
            print("Metrics po rozbalení:", metrics_after)
        else:
            print("Žádný vhodný vnitřní scrollovací kontejner jsem nenašel.")

    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(800)


def export_pdf(url, output_pdf):
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

        prepare_page_for_full_export(page)

        # Důležité:
        # Playwright při PDF defaultně používá print CSS.
        # Tohle zachová vzhled podobnější tomu, co vidíš v prohlížeči.
        page.emulate_media(media="screen")

        print("Exportuji PDF...")

        page.pdf(
            path=output_pdf,
            format="A4",
            print_background=True,
            margin={
                "top": "10mm",
                "right": "10mm",
                "bottom": "10mm",
                "left": "10mm"
            }
        )

        browser.close()
        print(f"Hotovo! PDF uloženo jako {output_pdf}")


if __name__ == "__main__":
    export_pdf(URL, OUTPUT_PDF)