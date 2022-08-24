# A tool to follow redirects

import requests
from flask import Flask, request

app = Flask(__name__)

############
# This method is if you want to make a request via a browser form.

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info('Started')

@app.route('/', methods=['GET', 'POST'])
def index():
    return '''
    <form action="/redirect" method="POST">
        <input type="text" name="url" placeholder="URL">
        <input type="submit" value="Submit">
    </form>
    '''

@app.route('/redirect', methods=['POST'])
def redirect_url():
    url = request.form['url']
    
    # if not URL provided, return error and link back to index
    if not url:
        return '<a href="/">Please enter a URL</a>'
    else:
        if not url.startswith('http') or not url.startswith('https'):
            url = 'http://' + url
        r = requests.get(url, allow_redirects=True)
        with open('history.log', 'a') as f:
            f.write(f"Initial URL: {url} ; Final URL: {r.url} '\n'")

        # Link to url and to index
        return '''
        <a href="{}">{}</a><br><br>
        <a href="/">Back to search</a>
        '''.format(r.url, r.url)

###########

# This method is if you want to make a request via curl.

@app.route('/search', methods=['GET'])
def process_request():
    url = request.args.get('url')

    if not url:
        return 'No URL provided'
    else:
        # add http if it's not there
        if not url.startswith('http') or not url.startswith('https'):
            url = 'http://' + url

        r = requests.get(url, allow_redirects=True)
       
        history = [(r.url, r.status_code)]
        while r.history:
            r = r.history[0]
            history.append((r.url, r.status_code))
    

        return '''
        <h1>History</h1>
        <ul>
        {}
        </ul>
        <a href="/">Back to search</a>
        '''.format(''.join(['<li><a href="{}">{}</a></li>'.format(url, url) for url, status_code in history]))
