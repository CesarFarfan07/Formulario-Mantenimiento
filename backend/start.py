import uvicorn
import sys, os

# Import config seed if available (syncs config from repo to DB)
try:
    from import_config import import_config
    import_config()
except Exception as e:
    print(f"[start.py] Config import skipped: {e}")

port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
