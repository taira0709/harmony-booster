[Harmony Booster - How to use]

1) Double-click Start.bat
   - On first run, it creates a virtual environment and installs required libraries.
   - Your browser will open http://localhost:8501

2) Use the app in the browser.

3) When finished, just close the browser tab. If needed, run Stop.bat to stop the server.

Troubleshooting:
- If a security dialog appears, allow the app to use the network locally.
- If the port 8501 is already used, edit Start.bat and change set PORT=8502 (and re-run).
- If something fails to import, add the missing package name to requirements.txt and re-run Start.bat.
