import os

from flask import Flask, render_template

app = Flask(__name__)

# autoreload of changes to template files
from os import path, walk
extra_dirs = ['templates','static']
extra_files = extra_dirs[:]
for extra_dir in extra_dirs:
    for dirname, dirs, files in walk(extra_dir):
        for filename in files:
            filename = path.join(dirname, filename)
            if path.isfile(filename):
                extra_files.append(filename)

@app.route('/hello')
def hello():
    return 'Hello, World!'

@app.route('/')
def index():
    return render_template('/index.html')

@app.route('/base')
def base():
    return render_template('/base.html')

if __name__ == "__main__":
    app.run(debug=True, extra_files=extra_files)