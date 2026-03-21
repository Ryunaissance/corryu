import http.server
import socketserver
import os

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle requests in a separate thread."""

if __name__ == '__main__':
    # Set the working directory to where index.html is located
    os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output'))
    
    port = 8081
    Handler = http.server.SimpleHTTPRequestHandler
    
    with ThreadedHTTPServer(("", port), Handler) as httpd:
        print(f"🚀 Multi-threaded CORRYU Dev Server running at http://localhost:{port}")
        print("💡 This server solves the CSS breaking issue on hard refresh.")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
