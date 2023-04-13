import logging
from logging.handlers import RotatingFileHandler
import requests
from flask import Flask, abort, render_template, request
from urllib.parse import urlparse, urlunparse

app = Flask(__name__)

log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
log_handler = RotatingFileHandler("app.log", maxBytes=10 * 1024 * 1024, backupCount=5)
log_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(log_handler)

logger.info("Application started")


def strip_query_string(url):
    parsed_url = urlparse(url)
    stripped_url = urlunparse(parsed_url._replace(query=''))
    return stripped_url


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        url = request.form["url"]
        strip_query_string_checkbox = request.form.get("strip_query_string") == "true"

        if not url:
            return render_template("index.html", error="Please enter a URL")

        if not (url.startswith("http") or url.startswith("https")):
            url = "http://" + url

        try:
            r = requests.get(url, allow_redirects=True, timeout=5)
            redirect_history = [(resp.url, resp.status_code) for resp in r.history]

            # Strip the query string from the final URL if the checkbox is checked
            final_url = strip_query_string(r.url) if strip_query_string_checkbox else r.url
            redirect_history.append((final_url, r.status_code))

            for i, (redirect_url, status_code) in enumerate(redirect_history):
                logger.info(
                    "Redirect %d: %s (Status code: %d)",
                    i + 1,
                    redirect_url,
                    status_code,
                )

            return render_template("result.html", history=redirect_history)
        except Exception as e:
            logger.exception("Error processing URL: %s", url)
            return render_template("index.html", error=f"Error processing URL: {e}")

    return render_template("index.html", error=None)



@app.errorhandler(404)
def page_not_found(e):
    logger.warning("Page not found: %s", request.url)
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    logger.error("Internal server error: %s", request.url)
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(port=8080, debug=True)

