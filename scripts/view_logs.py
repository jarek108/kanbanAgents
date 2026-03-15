import http.server
import socketserver
import webbrowser
import os

PORT = 8000
HANDLER = http.server.SimpleHTTPRequestHandler

# Ensure we are serving from the project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

print(f"Serving logs at http://localhost:{PORT}/render_logs.html")
print("Press Ctrl+C to stop.")

with socketserver.TCPServer(("", PORT), HANDLER) as httpd:
    webbrowser.open(f"http://localhost:{PORT}/render_logs.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping server.")
