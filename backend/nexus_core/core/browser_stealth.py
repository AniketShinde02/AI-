# browser_stealth.py
# ==================
# Responsibility: Houses JavaScript scripts injected into Chromium pages
# for DOM extraction, accessibility tree snapshotting, and stealth evasion.

_DOM_SNAPSHOT_JS = """
() => {
    const isVisible = (el) => {
        const r = el.getBoundingClientRect();
        const s = window.getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
    };
    const text = [];
    const buttons = [];
    const inputs = [];
    const links = [];

    // Collect visible text (paragraphs, headings, spans with meaningful text)
    document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, li, td, th, label, div[role]').forEach(el => {
        if (isVisible(el) && el.innerText && el.innerText.trim().length > 3) {
            const t = el.innerText.trim().replace(/\\s+/g, ' ');
            if (t.length < 500) text.push(t);
        }
    });

    // Buttons
    document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            buttons.push({
                text: (el.innerText || el.value || el.ariaLabel || '').trim().substring(0, 100),
                selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : 'button'),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    // Inputs
    document.querySelectorAll('input:not([type="hidden"]), textarea, [contenteditable="true"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            inputs.push({
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder || '',
                label: (el.labels && el.labels[0] ? el.labels[0].innerText : el.ariaLabel || '').trim().substring(0, 80),
                selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : 'input'),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    // Links
    document.querySelectorAll('a[href]').forEach(el => {
        if (isVisible(el) && el.innerText.trim().length > 1) {
            const r = el.getBoundingClientRect();
            links.push({
                text: el.innerText.trim().substring(0, 120),
                href: el.href.substring(0, 200),
                x: Math.round(r.x + r.width/2),
                y: Math.round(r.y + r.height/2),
            });
        }
    });

    return {
        url: window.location.href,
        title: document.title,
        text: [...new Set(text)].slice(0, 30),
        buttons: buttons.slice(0, 20),
        inputs: inputs.slice(0, 15),
        links: links.slice(0, 30),
    };
}
"""

_A11Y_TREE_JS = """
() => {
    const walk = (el, depth) => {
        if (depth > 4) return null;
        const role = el.getAttribute('role') || el.tagName.toLowerCase();
        const label = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.textContent?.trim().substring(0, 80) || '';
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return null;
        const node = {
            role,
            label,
            id: el.id || null,
            x: Math.round(r.x + r.width/2),
            y: Math.round(r.y + r.height/2),
            children: [],
        };
        const interestingChildren = Array.from(el.children).filter(c => {
            const cr = c.getBoundingClientRect();
            return cr.width > 0 && cr.height > 0;
        });
        for (const child of interestingChildren.slice(0, 5)) {
            const childNode = walk(child, depth + 1);
            if (childNode) node.children.push(childNode);
        }
        return node;
    };
    return walk(document.body, 0);
}
"""

_STEALTH_JS = """
// 1. Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
});

// 2. Spoof WebGL Renderer to match consumer devices
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (Apple)'; // UNMASKED_VENDOR_WEBGL
    if (parameter === 37446) return 'Apple GPU'; // UNMASKED_RENDERER_WEBGL
    return getParameter.apply(this, [parameter]);
};
const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (Apple)';
    if (parameter === 37446) return 'Apple GPU';
    return getParameter2.apply(this, [parameter]);
};

// 3. Spoof Chrome Plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { 0: { type: "application/x-google-chrome-pdf" }, description: "Portable Document Format", filename: "internal-pdf-viewer", length: 1, name: "Chrome PDF Plugin" },
        { 0: { type: "application/pdf" }, description: "", filename: "mhjimiokjillhjicmknhcjfoahelffjc", length: 1, name: "Chrome PDF Viewer" }
    ],
});

// 4. Spoof window.chrome
window.chrome = {
    app: { isInstalled: false },
    runtime: {}
};
"""
