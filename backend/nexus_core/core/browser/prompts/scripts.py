"""
browser/prompts/scripts.py
===========================
Nexus Browser Domain — Injected JavaScript Scripts

Single Responsibility: Centralise all JavaScript strings injected into Playwright
pages. This file is PURE DATA — no Python logic, no imports from other browser modules.
"""

DOM_SNAPSHOT_JS = """
() => {
    const isVisible = (el) => {
        const r = el.getBoundingClientRect();
        const s = window.getComputedStyle(el);
        return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
    };
    const text = [], buttons = [], inputs = [], links = [];

    document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, li, td, th, label, div[role]').forEach(el => {
        if (isVisible(el) && el.innerText && el.innerText.trim().length > 3) {
            const t = el.innerText.trim().replace(/\\s+/g, ' ');
            if (t.length < 500) text.push(t);
        }
    });
    document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            buttons.push({
                text: (el.innerText || el.value || el.ariaLabel || '').trim().substring(0, 100),
                selector: el.id ? '#' + el.id : (el.className ? '.' + el.className.split(' ')[0] : 'button'),
                x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
            });
        }
    });
    document.querySelectorAll('input:not([type="hidden"]), textarea, [contenteditable="true"]').forEach(el => {
        if (isVisible(el)) {
            const r = el.getBoundingClientRect();
            inputs.push({
                type: el.type || el.tagName.toLowerCase(),
                placeholder: el.placeholder || '',
                label: (el.labels && el.labels[0] ? el.labels[0].innerText : el.ariaLabel || '').trim().substring(0, 80),
                selector: el.id ? '#' + el.id : (el.name ? '[name="' + el.name + '"]' : 'input'),
                x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
            });
        }
    });
    document.querySelectorAll('a[href]').forEach(el => {
        if (isVisible(el) && el.innerText.trim().length > 1) {
            const r = el.getBoundingClientRect();
            links.push({
                text: el.innerText.trim().substring(0, 120),
                href: el.href.substring(0, 200),
                x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
            });
        }
    });
    return {
        url: window.location.href, title: document.title,
        text: [...new Set(text)].slice(0, 30),
        buttons: buttons.slice(0, 20), inputs: inputs.slice(0, 15), links: links.slice(0, 30),
    };
}
"""

A11Y_TREE_JS = """
() => {
    const walk = (el, depth) => {
        if (depth > 4) return null;
        const role = el.getAttribute('role') || el.tagName.toLowerCase();
        const label = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.textContent?.trim().substring(0, 80) || '';
        const r = el.getBoundingClientRect();
        if (r.width === 0 && r.height === 0) return null;
        const node = { role, label, id: el.id || null, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2), children: [] };
        const interestingChildren = Array.from(el.children).filter(c => { const cr = c.getBoundingClientRect(); return cr.width > 0 && cr.height > 0; });
        for (const child of interestingChildren.slice(0, 5)) {
            const childNode = walk(child, depth + 1);
            if (childNode) node.children.push(childNode);
        }
        return node;
    };
    return walk(document.body, 0);
}
"""

STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (Apple)';
    if (parameter === 37446) return 'Apple GPU';
    return getParameter.apply(this, [parameter]);
};
const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
WebGL2RenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Google Inc. (Apple)';
    if (parameter === 37446) return 'Apple GPU';
    return getParameter2.apply(this, [parameter]);
};
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { 0: { type: "application/x-google-chrome-pdf" }, description: "Portable Document Format", filename: "internal-pdf-viewer", length: 1, name: "Chrome PDF Plugin" },
        { 0: { type: "application/pdf" }, description: "", filename: "mhjimiokjillhjicmknhcjfoahelffjc", length: 1, name: "Chrome PDF Viewer" }
    ],
});
window.chrome = { app: { isInstalled: false }, runtime: {} };
"""

AGENTIC_SYSTEM_PROMPT = """You are a browser automation agent. Your job is to complete the user's goal by controlling a web browser.

At each iteration you will receive:
- GOAL: The overall objective
- CURRENT STATE: URL, page title, visible buttons, inputs, links, and text on screen
- HISTORY: Previous actions and results

Respond with a JSON object (ONLY JSON, no markdown) describing the NEXT single action to take:

{
  "action": "<action_name>",
  "target": "<CSS selector, URL, or text to interact with>",
  "text": "<text to type, if action=type>",
  "reasoning": "<1-2 sentence explanation>",
  "done": false
}

Available actions:
- open_url: Navigate to a URL. target = full URL.
- click: Click an element. target = CSS selector or visible text.
- type: Type text into a field. target = CSS selector. text = what to type.
- submit: Submit a form or press Enter. target = optional CSS selector.
- search: Type in the main search box and submit. target = search query.
- wait: Wait N seconds. target = number of seconds as string.
- verify_text: Check if text is visible. target = text to look for.
- scroll: Scroll the page down. target = "down" or "up".

If the goal is fully achieved, set "done": true.
If you cannot proceed (error loop, missing auth, bot detection), set "done": true with reasoning explaining why.

IMPORTANT: Output ONLY valid JSON. No backticks, no markdown, no extra text."""
