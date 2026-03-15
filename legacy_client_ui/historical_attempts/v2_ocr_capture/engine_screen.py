import mss
import argparse
import os
import sys

def take_screenshot(filename, screen_index):
    """
    Takes a screenshot of the specified screen and saves it as a .jpg.
    """
    # Create screenshots directory if it doesn't exist
    os.makedirs("screenshots", exist_ok=True)
    
    # Ensure filename ends with .jpg
    if not filename.lower().endswith(".jpg"):
        output_path = os.path.join("screenshots", f"{filename}.jpg")
    else:
        output_path = os.path.join("screenshots", filename)

    try:
        with mss.mss() as sct:
            # sct.monitors returns a list of dictionaries with monitor geometry
            # index 0 is the "all monitors" view, 1 is the first monitor, etc.
            # So user screen_index 0 should map to sct.monitors[1]
            monitors = sct.monitors
            
            # The user's 0-based index maps to mss's 1-based index (0 is all)
            mss_index = screen_index + 1
            
            if mss_index < 1 or mss_index >= len(monitors):
                print(f"Error: Screen index {screen_index} is out of range. Available: 0 to {len(monitors)-2}")
                return

            monitor = monitors[mss_index]
            print(f"Capturing screen {screen_index} (mss index {mss_index}): {monitor}")
            
            # Grab the data
            sct_img = sct.grab(monitor)
            
            # Convert to RGB and save as JPG using Pillow (mss provides raw pixels)
            from PIL import Image
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.save(output_path, "JPEG", quality=85)
            
            print(f"Screenshot saved successfully to {output_path}")
        
    except Exception as e:
        print(f"Error taking screenshot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture a screenshot of a specific screen.")
    parser.add_argument("filename", help="The name of the output file (without extension)")
    parser.add_argument("screen_index", type=int, default=0, nargs="?", help="Index of the screen to capture (default: 0)")
    
    args = parser.parse_args()
    take_screenshot(args.filename, args.screen_index)
