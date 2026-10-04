#!/usr/bin/env python3
import argparse, json, os
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

class H(SimpleHTTPRequestHandler):
    root=None; web=None
    def translate_path(self,path):
        p=urlparse(path).path
        return str(self.web/(p.lstrip("/") or "index.html"))
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/api/state":
            f=self.root/"results/demo/3d_demo_state.json"
            data={"phase":"idle","headline":"Waiting for a 3D demo scene..."}
            if f.exists():
                try: data=json.loads(f.read_text(encoding="utf-8"))
                except Exception: pass
            raw=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(raw)))
            self.end_headers(); self.wfile.write(raw); return
        super().do_GET()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=os.environ.get("REPO_ROOT") or os.getcwd())
    ap.add_argument("--port",type=int,default=8766)
    args=ap.parse_args()
    H.root=Path(args.repo_root).resolve()
    H.web=Path(__file__).resolve().parent.parent/"web"
    print(f"[3D HUD] http://127.0.0.1:{args.port}")
    ThreadingHTTPServer(("127.0.0.1",args.port),H).serve_forever()
if __name__=="__main__": main()
