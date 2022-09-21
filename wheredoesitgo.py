# A tool to follow redirects

import logging

import requests
from flask import Flask, request

app = Flask(__name__)

############
# This method is if you want to make a request via a browser form.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Started")


@app.route("/", methods=["GET", "POST"])
def index():
    return """
    <form action="/redirect" method="POST">
        <input type="text" name="url" placeholder="URL">
        <input type="submit" value="Submit">
    </form>
    """


@app.route("/redirect", methods=["POST"])
def redirect_url():
    url = request.form["url"]

    # if not URL provided, return error and link back to index
    if not url:
        return '<a href="/">Please enter a URL</a>'
    else:
        if not url.startswith("http") or not url.startswith("https"):
            url = "http://" + url
        r = requests.get(url, allow_redirects=True)
        with open("history.log", "a") as f:
            f.write(
                f"Initial URL: {url} ; Final URL: {r.url} ; Status Code:{r.status_code}; Method: GUI '\n'"
            )

        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="X-UA-Compatible" content="ie=edge">
            <title>Redirect</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.3/dist/css/bootstrap.min.css" integrity="sha384-TX8t27EcRE3e/ihU7zmQxVncDAy5uIKz4rEkgIXeMed4M0jlfIDPvg6uqKI2xXr2" crossorigin="anonymous>
        </head>
        <body>
            <div class="container">
                <h1>Trace Results</h1>
                <p>The final URL is: <a href="{r.url}">{r.url}</a></p>
                <p>Status Code: {r.status_code}</p>
                <a href="/">Back to home page</a>
            </div> 
        </body>
        </html>
        """

        # # Link to url and to index
        # return '''
        # <a href="{}">{}</a><br><br>
        # <a href="/">Back to search</a>
        # '''.format(r.url, r.url)


###########

# This method is if you want to make a request via curl.


@app.route("/search", methods=["GET"])
def process_request():
    url = request.args.get("url")

    if not url:
        return "No URL provided"
    else:
        # add http if it's not there
        if not url.startswith("http") or not url.startswith("https"):
            url = "http://" + url

        r = requests.get(url, allow_redirects=True)
        with open("history.log", "a") as f:
            f.write(
                f"Initial URL: {url} ; Final URL: {r.url} ; Status Code:{r.status_code}; Method:API '\n'"
            )

        history = [(r.url, r.status_code)]
        while r.history:
            r = r.history[0]
            history.append((r.url, r.status_code))

        return """
        <h1>History</h1>
        <ul>
        {}
        </ul>
        <a href="/">Back to search</a>
        """.format(
            "".join(
                [f'<li><a href="{url}">{url}</a></li>' for url, status_code in history]
            )
        )


# app.run(port=8080, debug=True)
