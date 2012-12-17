Ship Scan Cost Estimator
========================
Tool to use in Eve Online for evaluating the value of a ship's cargo based on cargo scan results.

Requirements
============
* Python >= 2.6
* Flask
* Memcache
* en-US Locale

First Run
=========
First, you need to download the source.
```
git clone https://github.com/sudorandom/cargoscanner.git
cd cargoscanner
```

Install requirements
```
pip install -r requirements.txt
```

Start the app
```
python cargoscanner.py
```

Deployment
==========
I deploy with uWSGI, nginx and supervisor but Flask is very flexable. It will also easily work with fastcgi, mod_wsgi, gunicorn, etc etc. [More details here](http://flask.pocoo.org/docs/deploying/).

License
=======
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.