# APM Automatic Instrumentation - must be first import
from ddtrace import patch_all
patch_all()

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5050)