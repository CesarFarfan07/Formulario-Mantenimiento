import uvicorn
import sys, os
port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", 8000))
uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
