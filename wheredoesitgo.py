#!/usr/bin/env python3

"""
Where Does It Go?

A secure redirect tracker with SSRF protection. Inspired by https://wheregoes.com
"""

import ipaddress
import logging
import socket
from logging.handlers import RotatingFileHandler
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Logging setup
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
    """Remove query string from a URL for display purposes."""
    parsed_url = urlparse(url)
    stripped_url = urlunparse(parsed_url._replace(query=""))
    return stripped_url


def trace_redirects(start_url, max_redirects=10):
    """
    Manually traverses HTTP redirects to evaluate SSRF constraints at each hop
    and prevent resource exhaustion via stream=True.
    """
    current_url = start_url
    history = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for step in range(max_redirects):
        parsed = urlparse(current_url)
        if not parsed.hostname:
            return history, f"Invalid URL at hop {step}: {current_url}"

        try:
            # Resolve and validate IP to prevent SSRF
            ip = socket.gethostbyname(parsed.hostname)
            parsed_ip = ipaddress.ip_address(ip)
            if parsed_ip.is_loopback or parsed_ip.is_private or parsed_ip.is_link_local:
                return history, f"Blocked private IP at hop {step}: {current_url}"
        except socket.gaierror:
            return history, f"DNS resolution failed at hop {step}: {current_url}"

        try:
            # We use the original current_url instead of IP-pinning to preserve TLS/SNI.
            # This accepts a minor TOCTOU risk in favor of functional HTTPS requests.
            resp = requests.get(
                current_url,
                allow_redirects=False,
                timeout=5,
                headers=headers,
                stream=True,
            )
            resp.close()

            history.append({"url": current_url, "status_code": resp.status_code})

            if (
                resp.status_code in (301, 302, 303, 307, 308)
                and "Location" in resp.headers
            ):
                next_url = resp.headers["Location"]
                current_url = urljoin(current_url, next_url)
            else:
                break

        except requests.exceptions.RequestException as e:
            # Log the full error internally, return generic error to prevent info disclosure
            logger.error("Request failed for %s: %s", current_url, str(e))
            return history, "Request failed - check URL or try again later"

    return history, None


@app.route("/", methods=["GET", "POST"])
def index():
    """Main route handling HTML frontend requests."""
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        strip_query_string_checkbox = request.form.get("strip_query_string") == "true"

        if not url:
            return render_template("index.html", error="Please enter a URL")

        # Case-insensitive protocol check
        if not url.lower().startswith(("http://", "https://")):
            url = "http://" + url

        redirect_history, error_message = trace_redirects(url, max_redirects=10)

        if error_message:
            logger.warning("Redirect processing failed for %s: %s", url, error_message)
            return render_template("index.html", error=error_message)

        # Empty history crash prevention
        if not redirect_history:
            return render_template(
                "index.html", error="Could not process URL - no redirects found"
            )

        # Apply query stripping to final URL if requested
        if strip_query_string_checkbox:
            redirect_history[-1]["url"] = strip_query_string(
                redirect_history[-1]["url"]
            )

        for i, redirect_data in enumerate(redirect_history):
            logger.info(
                "Redirect %d: %s (Status: %d)",
                i + 1,
                redirect_data["url"],
                redirect_data["status_code"],
            )

        return render_template("result.html", history=redirect_history)

    return render_template("index.html", error=None)


@app.route("/api/trace", methods=["GET", "POST"])
def api_trace():
    """Programmable API endpoint for Apple Shortcuts."""
    data = request.get_json() if request.is_json else request.values
    url = data.get("url", "").strip()
    strip_query = str(data.get("strip_query_string", "")).lower() == "true"

    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # Case-insensitive protocol check
    if not url.lower().startswith(("http://", "https://")):
        url = "http://" + url

    redirect_history, error_message = trace_redirects(url, max_redirects=10)

    if error_message:
        return jsonify({"error": error_message}), 400

    # Empty history crash prevention
    if not redirect_history:
        return jsonify({"error": "Could not process URL - no redirects found"}), 400

    final_url = redirect_history[-1]["url"]
    if strip_query:
        final_url = strip_query_string(final_url)
        redirect_history[-1]["url"] = final_url

    return jsonify(
        {"original_url": url, "final_url": final_url, "history": redirect_history}
    ), 200


# Custom error handlers
@app.errorhandler(404)
def page_not_found(e):
    logger.warning("Page not found: %s", request.url)
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    logger.warning("Forbidden access: %s", request.url)
    return render_template("403.html"), 403


@app.errorhandler(500)
def internal_server_error(e):
    logger.error("Internal server error: %s", request.url)
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(port=8080, debug=True)
