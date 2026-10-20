from playwright.sync_api import sync_playwright

html = """<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>mermaid.initialize({startOnLoad: true, theme: 'default'});</script>
</head>
<body>
    <h1>Mermaid Test</h1>
    <div class="mermaid">
    flowchart TD
        A[Start] --> B{Is it working?}
        B -- Yes --> C[Great!]
        B -- No --> D[Debug]
    </div>
</body>
</html>"""

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", headless=True)
    page = browser.new_page()
    page.set_content(html, wait_until="networkidle")
    page.wait_for_selector(".mermaid svg", timeout=15000)
    print("Mermaid SVG rendered successfully!")
    page.pdf(path="test_mermaid.pdf")
    browser.close()
    print("PDF saved successfully!")
