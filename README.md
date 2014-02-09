Evepraisal
==========
This is a tool for Eve Online aimed at being able to quickly price check items. [Shown here](http://evepraisal.com).

Requirements
============
* Python > 2.7
* Flask
* Memcache

First Run
=========
First, you need to download the source.
```
git clone https://github.com/sudorandom/evepraisal.git
cd evepraisal
```

Install requirements
```
pip install -r requirements.txt
```

Start the app
```
python wsgi.py
```

Deployment
==========
I deploy with uWSGI, nginx and supervisor but Flask is very flexable. It will also easily work with fastcgi, mod_wsgi, gunicorn, etc etc. [More details here](http://flask.pocoo.org/docs/deploying/).

License
=======
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

CCP Copyright Notice
====================
EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved worldwide. All other trademarks are the property of their respective owners. EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots, characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are likewise the intellectual property of CCP hf. CCP hf. has granted permission to Evepraisal.com to use EVE Online and all associated logos and designs for promotional and information purposes on its website but does not endorse, and is not in any way affiliated with, Evepraisal.com. CCP is in no way responsible for the content on or functioning of this website, nor can it be liable for any damage arising from the use of this website.


[![Bitdeli Badge](https://d2weczhvl823v0.cloudfront.net/sudorandom/evepraisal/trend.png)](https://bitdeli.com/free "Bitdeli Badge")

