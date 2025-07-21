from app import create_app
from ddtrace import patch_all
patch_all()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5050)