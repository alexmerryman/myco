# app.py
from flask import Flask, redirect, url_for

from config import SECRET_KEY
from inat_auth import auth_bp
from viewer import viewer_bp
from uploader import uploader_bp


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(viewer_bp)
    app.register_blueprint(uploader_bp)

    @app.route("/tools")
    def tools():
        """Optional landing page listing both tools."""
        return redirect(url_for("viewer.index"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
