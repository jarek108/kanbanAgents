import argparse
import os
import sys
import time
from pathlib import Path

# Try to import playwright, if not installed, we'll guide the user
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("Error: 'playwright' library not found.")
    print("Please install it using:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)

def research_perplexity(md_file, request_content, model=None, deep_research=False, setup_mode=False, headful=False):
    # Determine session directory
    base_dir = Path(__file__).parent.parent
    session_dir = base_dir / ".perplexity_session"
    
    # Determine headless mode
    headless = True
    if setup_mode or headful:
        headless = False
        
    with sync_playwright() as p:
        # Launch persistent context to keep login session
        # Use a realistic user agent to avoid some bot detection
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(session_dir),
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.pages[0] if context.pages else context.new_page()
        
        start_load = time.perf_counter()
        print(f"Navigating to Perplexity.ai...")
        # Use 'domcontentloaded' to proceed as soon as the HTML is ready, rather than waiting for all assets
        page.goto("https://www.perplexity.ai/", wait_until="domcontentloaded")
        
        if setup_mode:
            print("\nSETUP MODE ENABLED")
            print("Please log in to your Perplexity account in the browser window.")
            print("Once you are logged in and ready, close the browser window or press Ctrl+C here.")
            try:
                # Wait indefinitely until the window is closed
                page.wait_for_event("close", timeout=0)
            except:
                pass
            print("Setup complete. Session saved.")
            return

        # 1. Fill request content
        print(f"Executing research: {request_content[:50]}...")
        
        # Combined selector to find the input field quickly without sequential timeouts
        input_selector = "textarea[placeholder*='Ask anything'], textarea, [contenteditable='true'], [role='textbox']"
        
        try:
            # Wait for any of the common input selectors to appear
            input_element = page.wait_for_selector(input_selector, timeout=10000)
            load_time = time.perf_counter() - start_load
        except:
            print("Error: Could not find input field on Perplexity.ai. The page might still be loading or has changed.")
            # If we are in headful mode, let the user see what happened
            if not headful:
                context.close()
            return

        if not input_element:
            print("Error: Input field found but is null.")
            if not headful:
                context.close()
            return

        # 2. Handle Deep Research (Pro) toggle if requested
        if deep_research:
            print("Attempting to enable Deep Research (Pro)...")
            try:
                # Perplexity often has a 'Pro' toggle
                pro_toggle = page.get_by_text("Pro", exact=True)
                if pro_toggle.is_visible():
                    pro_toggle.click()
                    time.sleep(0.5)
            except Exception as e:
                print(f"Warning: Could not toggle Pro/Deep Research: {e}")

        # 3. Handle Model Selection if requested
        if model:
            print(f"Attempting to select model: {model}...")
            try:
                # Look for a model selector button
                model_btn = page.locator("button").filter(has_text=True).filter(has_text="Model")
                if model_btn.is_visible():
                    model_btn.click()
                    page.get_by_text(model, exact=False).first.click()
            except Exception as e:
                print(f"Warning: Could not set model '{model}': {e}")

        # 4. Input text and Submit
        input_element.fill(request_content)
        start_response = time.perf_counter()
        page.keyboard.press("Enter")
        
        # 5. Wait for completion
        print("Waiting for response (this may take a while for deep research)...")
        
        # Selectors for state detection
        stop_selector = "button[aria-label*='Stop'], button:has(svg[data-icon='stop'])"
        copy_selector = "button[aria-label*='Copy'], button:has(svg[data-icon='copy'])"
        
        try:
            # Wait for EITHER the Stop button (started) or Copy button (already finished)
            combined_selector = f"{stop_selector}, {copy_selector}"
            page.wait_for_selector(combined_selector, timeout=30000)
            
            # If the stop button is visible, we need to wait for it to disappear
            if page.locator(stop_selector).is_visible():
                print("Generation in progress...")
                page.wait_for_selector(stop_selector, state="hidden", timeout=240000) # 4 min for very deep research
            
            # Final check to ensure the Copy button is there
            page.wait_for_selector(copy_selector, timeout=15000)
            
            # Minimal grace period for DOM to stabilize
            time.sleep(1)
            response_time = time.perf_counter() - start_response
            print("Response complete.")
        except PlaywrightTimeoutError:
            response_time = time.perf_counter() - start_response
            print("Timeout waiting for response to finish. Capturing current state.")

        # 6. Extract the content
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
                print("Warning: Could not find prose container, falling back to body text.")
                content = page.locator("body").inner_text()
                
            save_path = Path(md_file)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(f"# Perplexity Research: {request_content[:100]}\n\n")
                if model:
                    f.write(f"*Model: {model}*\n")
                if deep_research:
                    f.write(f"*Mode: Deep Research*\n")
                f.write(f"*Date: {time.strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
                f.write("-" * 40 + "\n\n")
                f.write(content)
                
            print(f"Results saved to: {md_file}")
            print(f"Metrics: Load Time: {load_time:.2f}s | Response Wait: {response_time:.2f}s")
            
            if headful:
                print("\nResearch complete. Browser kept open for inspection.")
                print("Close the browser window or press Ctrl+C to exit.")
                try:
                    page.wait_for_event("close", timeout=0)
                except:
                    pass
                
        except Exception as e:
            print(f"Error extracting content: {e}")

        context.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Research via Perplexity.ai")
    parser.add_argument("md_file", nargs="?", help="Path to save the results as a Markdown file")
    parser.add_argument("request_content", nargs="?", help="The query/request for research")
    parser.add_argument("--model", help="Optional model name to select")
    parser.add_argument("--deep-research", action="store_true", help="Enable Deep Research (Pro mode)")
    parser.add_argument("--headful", action="store_true", help="Run in visible mode and keep browser open")
    parser.add_argument("--setup", action="store_true", help="Run in visible mode to log in manually")
    
    args = parser.parse_args()
    
    if args.setup:
        research_perplexity(None, None, setup_mode=True)
    elif not args.md_file or not args.request_content:
        parser.print_help()
        print("\nExample: python tools/research_perplexity.py results.md \"What is the state of fusion energy?\" --deep-research")
    else:
        research_perplexity(args.md_file, args.request_content, args.model, args.deep_research, headful=args.headful)
