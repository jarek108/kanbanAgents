import sys
import argparse
import os
import time
from pathlib import Path
import re

# Try to import playwright, if not installed, we'll guide the user
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: 'playwright' library not found.", file=sys.stderr)
    print("Please install it using:", file=sys.stderr)
    print("  pip install playwright", file=sys.stderr)
    print("  playwright install chromium", file=sys.stderr)
    sys.exit(1)

def eprint(*args, **kwargs):
    kwargs['file'] = sys.stderr
    print(*args, **kwargs)

def research_perplexity(request_content, md_file=None, model=None, deep_research=False, setup_mode=False, headful=False):
    # Determine session directory
    base_dir = Path(__file__).parent.parent
    session_dir = base_dir / ".perplexity_session"
    
    # Determine headless mode
    headless = True
    if setup_mode or headful:
        headless = False
        
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        start_load = time.perf_counter()
        eprint(f"Navigating to Perplexity.ai...")
        page.goto("https://www.perplexity.ai/", wait_until="domcontentloaded")
        
        if setup_mode:
            eprint("\nSETUP MODE ENABLED")
            eprint("Please log in to your Perplexity account in the browser window.")
            eprint("Once you are logged in and ready, close the browser window or press Ctrl+C here.")
            try:
                page.wait_for_event("close", timeout=0)
            except:
                pass
            eprint("Setup complete. Session saved.")
            return

        eprint(f"Executing research: {request_content[:50]}...")
        input_selector = "textarea[placeholder*='Ask anything'], textarea, [contenteditable='true'], [role='textbox']"
        
        try:
            input_element = page.wait_for_selector(input_selector, timeout=10000)
            load_time = time.perf_counter() - start_load
        except:
            eprint("Error: Could not find input field on Perplexity.ai. The page might still be loading or has changed.")
            if not headful: context.close()
            return

        if not input_element:
            eprint("Error: Input field found but is null.")
            if not headful: context.close()
            return

        if deep_research:
            eprint("Attempting to enable Deep Research (Pro)...")
            try:
                pro_toggle = page.get_by_text("Pro", exact=True)
                if pro_toggle.is_visible():
                    pro_toggle.click()
                    time.sleep(0.5)
            except Exception as e:
                eprint(f"Warning: Could not toggle Pro/Deep Research: {e}")

        if model:
            eprint(f"Attempting to select model: {model}...")
            try:
                model_btn = page.locator("button").filter(has_text=True).filter(has_text="Model")
                if model_btn.is_visible():
                    model_btn.click()
                    page.get_by_text(model, exact=False).first.click()
            except Exception as e:
                eprint(f"Warning: Could not set model '{model}': {e}")

        input_element.fill(request_content)
        start_response = time.perf_counter()
        page.keyboard.press("Enter")
        
        eprint("Waiting for response (this may take a while for deep research)...")
        
        stop_selector = "button[aria-label*='Stop'], button:has(svg[data-icon='stop'])"
        copy_selector = "button[aria-label*='Copy'], button:has(svg[data-icon='copy'])"
        
        try:
            combined_selector = f"{stop_selector}, {copy_selector}"
            page.wait_for_selector(combined_selector, timeout=30000)
            
            if page.locator(stop_selector).is_visible():
                eprint("Generation in progress...")
                page.wait_for_selector(stop_selector, state="hidden", timeout=240000) 
            
            page.wait_for_selector(copy_selector, timeout=15000)
            time.sleep(1)
            response_time = time.perf_counter() - start_response
            eprint("Response complete.")
        except PlaywrightTimeoutError:
            response_time = time.perf_counter() - start_response
            eprint("Timeout waiting for response to finish. Capturing current state.")

        try:
            content = ""
            answer_locators = [
                "div.prose",
                ".col-start-1.col-end-13",
                "[role='main'] .prose",
            ]
            
            for selector in answer_locators:
                elements = page.locator(selector).all()
                if elements:
                    content = elements[-1].inner_text()
                    if content and len(content) > 50:
                        break
            
            if not content:
                eprint("Warning: Could not find prose container, falling back to body text.")
                content = page.locator("body").inner_text()
            
            # Generate markdown content
            full_markdown = f"# Perplexity Research: {request_content[:100]}\n\n"
            if model: full_markdown += f"*Model: {model}*\n"
            if deep_research: full_markdown += f"*Mode: Deep Research*\n"
            full_markdown += f"*Date: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
            full_markdown += "-" * 40 + "\n\n"
            full_markdown += content

            # Handle automatic filename if not provided
            if not md_file:
                safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', request_content[:30]).strip('_').lower()
                date_str = time.strftime('%Y-%m-%d')
                md_file = base_dir / "docs" / "research_notes" / f"{date_str}_{safe_name}.md"
            
            save_path = Path(md_file)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(full_markdown)
                
            eprint(f"Results saved to: {save_path}")
            eprint(f"Metrics: Load Time: {load_time:.2f}s | Response Wait: {response_time:.2f}s")
            
            # Output the content to stdout for Gemini CLI to capture
            print(full_markdown)
            
            if headful:
                eprint("\nResearch complete. Browser kept open for inspection.")
                eprint("Close the browser window or press Ctrl+C to exit.")
                try:
                    page.wait_for_event("close", timeout=0)
                except:
                    pass
                
        except Exception as e:
            eprint(f"Error extracting content: {e}")

        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research via Perplexity.ai")
    parser.add_argument("query", nargs="*", help="The query/request for research")
    parser.add_argument("--out", dest="md_file", help="Optional path to save the results as a Markdown file")
    parser.add_argument("--model", help="Optional model name to select")
    parser.add_argument("--deep-research", action="store_true", help="Enable Deep Research (Pro mode)")
    parser.add_argument("--headful", action="store_true", help="Run in visible mode and keep browser open")
    parser.add_argument("--setup", action="store_true", help="Run in visible mode to log in manually")
    
    args = parser.parse_args()
    
    if args.setup:
        research_perplexity(None, setup_mode=True)
    elif not args.query:
        parser.print_help()
        eprint("\nExample: python scripts/research_perplexity.py \"What is the state of fusion energy?\" --deep-research")
    else:
        query_str = " ".join(args.query)
        research_perplexity(query_str, md_file=args.md_file, model=args.model, deep_research=args.deep_research, headful=args.headful)
