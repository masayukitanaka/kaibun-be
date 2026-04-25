from flask import Flask

from src.ping import ping_bp
from src.palindrome import palindrome_bp
from src.download import download_bp

app = Flask(__name__)
app.register_blueprint(ping_bp)
app.register_blueprint(palindrome_bp)
app.register_blueprint(download_bp)


@app.route("/")
def hello():
    return "Hello, Cloud Run!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
