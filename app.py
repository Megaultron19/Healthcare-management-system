"""Entry point. Vercel imports `app` from here; locally run `python app.py` or `flask --app app run`."""
import os

from healthcare import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", 5000)))
