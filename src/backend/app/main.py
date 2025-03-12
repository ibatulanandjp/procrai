import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "my_best_kept_secret")

    from api.routes import api_blueprint

    app.register_blueprint(api_blueprint, url_prefix="/api")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
