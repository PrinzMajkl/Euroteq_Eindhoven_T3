import os
from playwright.sync_api import sync_playwright

def export_deck_to_pdf():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(script_dir, "deck_preview.html")
    pdf_path = os.path.join(script_dir, "plumetrace_presentation.pdf")
    
    print(f"Reading HTML from: {html_path}")
    print(f"Exporting PDF to:  {pdf_path}")
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="msedge")
            
        page = browser.new_page(viewport={"width": 1920, "height": 1080})
        page.goto(f"file:///{html_path.replace(os.sep, '/')}")
        page.wait_for_timeout(1000)
        page.pdf(
            path=pdf_path,
            width="16in",
            height="9in",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"}
        )
        browser.close()
        
    print("Export completed successfully!")

if __name__ == "__main__":
    export_deck_to_pdf()
