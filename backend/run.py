import os
import sys
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402

app = create_app(os.environ.get("FLASK_ENV", "development"))

if __name__ == "__main__":
    port = 5000

    for arg in sys.argv:
        if arg.startswith("--port="):
            port = int(arg.split("=")[1])

    app.run(host="127.0.0.1", port=port)
