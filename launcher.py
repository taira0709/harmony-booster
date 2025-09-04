# launcher.py
import os, sys, time, socket, webbrowser, urllib.request
from pathlib import Path

# 1) devモード無効
os.environ["STREAMLIT_GLOBAL_DEVELOPMENTMODE"] = "false"

# 2) appのパス
base_dir = Path(__file__).resolve().parent
app_path = base_dir / "app_streamlit_ms.py"
if not app_path.exists():
    print("ERROR: app_streamlit_ms.py not found.")
    sys.exit(1)

def find_free_port(start=8501, tries=20):
    port = start
    for _ in range(tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                port += 1
    return start  # 最後までダメなら開始値

PORT = find_free_port(8501)

# 3) Streamlitに使わせるポートを固定
os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)

def wait_then_open(url, timeout=40):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status < 400:
                    webbrowser.open_new_tab(url)
                    return
        except Exception:
            pass
        time.sleep(0.5)

# 4) 起動確認→開く（/_stcore/health でもOKだが rootで十分）
url = f"http://127.0.0.1:{PORT}/"
import threading
threading.Thread(target=wait_then_open, args=(url,), daemon=True).start()

# 5) Streamlit起動
from streamlit.web import cli as stcli
sys.argv = [
    "streamlit", "run", str(app_path),
    "--server.headless", "true",
    "--browser.gatherUsageStats", "false",
    "--global.developmentMode", "false",
]
sys.exit(stcli.main())
