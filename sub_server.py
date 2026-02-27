from flask import Flask, send_file, request
import os

app = Flask(__name__)
TOKEN = os.getenv("SUB_TOKEN")

@app.route('/sub')
def sub():
    if not TOKEN or request.args.get('token') != TOKEN:
        return "Access denied", 403
    return send_file('/sub_content.txt', mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)