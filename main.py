import cgi
import datetime
import urllib
import webapp2
import json
import logging
import urlparse
import base64
# import requests

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.ext import blobstore
from google.appengine.api import taskqueue
from google.appengine.api import urlfetch
import lib.cloudstorage as gcs

from models import *


################################################################################
"""The home page of the app"""
class HomeHandler(webapp2.RequestHandler):

    """Show the webform when the user is on the home page"""
    def get(self):

        if (self.request.headers.get('User-Agent') != "curl"):

            id_token = self.request.cookies.get("id_token")

            if id_token == None:
                self.response.write('Please authenticate first, using url "/user/authenticate/?username={USERNAME}&password={PASSWORD}".')

            else: 
                self.response.out.write('<html><body>')

                # Print out some stats on caching
                stats = memcache.get_stats()
                self.response.write('<b>Cache Hits:{}</b><br>'.format(stats['hits']))
                self.response.write('<b>Cache Misses:{}</b><br><br>'.format(
                                    stats['misses']))

                user = self.request.get('user')
                ancestor_key = ndb.Key("User", user or "*notitle*")
                # Query the datastore
                photos = Photo.query_user(ancestor_key).fetch(100)

                form = "<form action=\"/post/default/?id_token="+id_token+"""\" enctype="multipart/form-data" method="post">
                <div><textarea name="caption" rows="3" cols="60"></textarea></div>
                <div><label>Photo:</label></div>
                <div><input type="file" name="image"/></div>
                <div>User <input value="default" name="user"></div>
                <div>

                    <input type="submit" value="Post">
                </div>
                </form>
                <hr>
                </body>
                </html>"""
                self.response.write(form)


################################################################################
"""Handle activities associated with a given user"""
class UserHandler(webapp2.RequestHandler):

    """Print json or html version of the users photos"""
    def get(self,user,type):
        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_user(user, id_token):
                if (self.request.headers.get('User-Agent') != "curl"):
                    self.response.set_cookie('id_token', id_token, max_age=3600, path='/')
                #ancestor_key = ndb.Key("User", user)
                #photos = Photo.query_user(ancestor_key).fetch(100)
                photos = self.get_data(user)
                if type == "json":
                    output = self.json_results(photos, user)
                else:
                    output = self.web_results(photos, user)
                self.response.out.write(output)
            else: 
                self.response.out.write("401 No Authorization \r\n") 
                self.response.set_status(401)
        else: 
            self.response.out.write("401 No Authorization \r\n") 
            self.response.set_status(401)

    def json_results(self,photos,user):
        """Return formatted json from the datastore query"""
        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        id_token = query['id_token'][0]

        json_array = []
        for photo in photos:
            dict = {}
            dict['image_url'] = "image/" + photo.key.urlsafe() + "/?id_token=" + id_token
            dict['caption'] = photo.caption
            dict['user'] = user
            dict['date'] = str(photo.date)
            json_array.append(dict)
        return json.dumps({'results' : json_array})

    def web_results(self,photos,user):
        """Return html formatted json from the datastore query"""
        html = ""
        for photo in photos:
            html += '<div><hr><div><img src="/image/%s/" width="200" border="1"/></div>' % photo.key.urlsafe()
            html += '<div><blockquote>Caption: %s<br>User: %s<br>Date:%s</blockquote></div></div>' % (cgi.escape(photo.caption),user,str(photo.date))
        return html

    @staticmethod
    def get_data(user):
        """Get data from the datastore only if we don't have it cached"""
        key = user + "_photos"
        data = memcache.get(key)
        if data is not None:
            logging.info("Found in cache")
            return data
        else:
            logging.info("Cache miss")
            ancestor_key = ndb.Key("User", user)
            data = Photo.query_user(ancestor_key).fetch(100)
            if not memcache.add(key, data, 3600):
                logging.info("Memcache failed")
        return data

################################################################################
"""Handle requests for an image ebased on its key"""
class ImageHandler(webapp2.RequestHandler):

    def get(self,key):
        """Write a response of an image (or 'no image') based on a key"""
        photo = ndb.Key(urlsafe=key).get()

        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)

        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_photo_user(key, id_token):
                self.response.set_cookie('id_token', id_token, max_age=3600, path='/')
                if blobstore.BlobReader(photo.b_key):
                    blob_reader = blobstore.BlobReader(photo.b_key)
                    blob_reader_data = blob_reader.read()
                    self.response.headers['Content-Type'] = 'image/png'
                    self.response.write(blob_reader_data)
                else:
                    self.response.out.write("No image")
            else:
                self.response.out.write("401 No Authorization \r\n") 
                self.response.set_status(401)
        else:
            self.response.out.write("401 No Authorization \r\n") 
            self.response.set_status(401)


################################################################################
class PostHandler(webapp2.RequestHandler):

    def post(self,user):

        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_user(user, id_token):

                # If we are submitting from the web form, we will be passing
                # the user from the textbox.  If the post is coming from the
                # API then the username will be embedded in the URL
                if self.request.get('user'):
                    user = self.request.get('user')

                # Be nice to our quotas
                image = self.request.get('image')
                thumbnail = images.resize(image, 30,30)

                # Create and add a new Photo entity
                #
                # We set a parent key on the 'Photos' to ensure that they are all
                # in the same entity group. Queries across the single entity group
                # will be consistent. However, the write rate should be limited to
                # ~1/second.
                photo = Photo(parent=ndb.Key("User", user),
                        caption=self.request.get('caption'),
                        labels=[],
                        )
                photo_key = photo.put()

                # Store the image into Google Cloud Storage
                bucket = 'phototimeline'
                nameofFile = photo_key.urlsafe()
                fileName='/'+bucket+'/'+nameofFile
                blob_key = self.CreateFile(fileName,thumbnail)
                p = photo_key.get()
                p.b_key = blob_key
                p.put()

                # Store the image key into the corresponding user entity
                the_user = User.query(User.username == user).get()
                the_user.photos.append(photo_key)
                the_user.put()

                # Push photo into task queue
                task = taskqueue.add(
                    url='/label_task',
                    params={
                        'photo_key': nameofFile, 
                    })

                # Clear the cache (the cached version is going to be outdated)
                key = user + "_photos"
                memcache.delete(key)

                # Redirect to print out JSON
                self.redirect('/user/'+user+'/json/?id_token='+id_token)

            else:
                self.response.out.write("401 No Authorization \r\n") 
                self.response.set_status(401)
        else:
            self.response.out.write("401 No Authorization \r\n") 
            self.response.set_status(401)

    @staticmethod
    def CreateFile(filename,imageFile):
        with gcs.open(filename, 'w', content_type = 'image/jpeg') as f:
            f.write(imageFile)
            f.close()

        blobstore_filename = '/gs' + filename
        return blobstore.create_gs_key(blobstore_filename)


################################################################################
"""Demonstrate the different levels of logging"""
class LoggingHandler(webapp2.RequestHandler):

    def get(self):
        logging.debug('This is a debug message')
        logging.info('This is an info message')
        logging.warning('This is a warning message')
        logging.error('This is an error message')
        logging.critical('This is a critical message')

        try:
            raise ValueError('This is a sample value error.')
        except ValueError:
            logging.exception('A example exception log.')

        self.response.out.write('Logging example.')


################################################################################
"""Delete a photo"""
class DeleteHandler(webapp2.RequestHandler):

    def get(self, key):

        photo_key = ndb.Key(urlsafe=key)

        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)

        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_photo_user(key, id_token):
                self.response.set_cookie('id_token', id_token, max_age=3600, path='/')
                
                # Delete from storage
                blobstore.delete(photo_key.get().b_key)
                # Remove record from the corresponding user entity
                User.delete_photo(photo_key, id_token)
                # Delete the corresponding photo entity
                photo_key.delete()

                self.response.out.write("Successfully deleted. \r\n")
            else: 
                self.response.out.write("401 No Authorization \r\n") 
                self.response.set_status(401)
        else: 
            self.response.out.write("401 No Authorization \r\n") 
            self.response.set_status(401)


################################################################################
"""Authenticate a user and return id_token"""
class AuthHandler(webapp2.RequestHandler):

    def get(self):

        psw = ""

        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)
        if 'password' in query:
            psw = query['password'][0]

        if 'username' in query:
            username = query['username'][0]

            user = User.query(User.username == username).get()
            # if user is in datastore, store key(id) as id_token
            if user:
                id_token = user.key.urlsafe()
            # else, store new user to datastore, store key(id) as id_token
            else:
                if len(psw) > 0:
                    new_user = User(username=username)
                    new_user.put().urlsafe()
                else:
                    new_user = User(username=username,
                        password=psw)
                    new_user.put().urlsafe()
                    id_token = new_user.put().urlsafe()

            # store id_token into browser cookies
            self.response.set_cookie('id_token', id_token, max_age=3600, path='/')

            json_array = []
            dict = {}
            dict['username'] = username
            dict['id_token'] = id_token
            json_array.append(dict)
            output = json.dumps({'results' : json_array})

        else:
            output = "Please enter a valid username."
        self.response.out.write(output)


################################################################################
"""Handel for task label photos"""
class LabelTaskHandler(webapp2.RequestHandler):

    def post(self):
        photo_key = self.request.get('photo_key')

        # submit task to google cloud vision to detect labels
        API_ENDPOINT = "https://vision.googleapis.com/v1/images:annotate"
        API_KEY = "AIzaSyCDQH6fKwAOoaJiTJ2qk6zw2dYZfCb2dlc"

        url = API_ENDPOINT + "?key=" + API_KEY
        data = {
            "requests": [
                {
                    "image":{
                        "source":{"imageUri":"gs://phototimeline/"+photo_key}
                    },
                    "features":[{"type":"LABEL_DETECTION"}]
                }
            ]
        }

        # response = requests.post(url = url, data = json.dumps(data))
        content = urlfetch.fetch(url=url, payload=json.dumps(data), headers={"Content-Type": "application/json"}, method=urlfetch.POST).content
        response = json.loads(content)['responses']
        label_annos = response[0]['labelAnnotations'][0:3]

        # update photo entity in datastore to add labels
        labels = []
        for anno in label_annos:
            labels.append(anno['description'])
        photo = ndb.Key(urlsafe=photo_key).get()
        photo.labels = labels
        photo.put()


################################################################################

app = webapp2.WSGIApplication([
    ('/', HomeHandler),
    ('/label_task', LabelTaskHandler),
    webapp2.Route('/logging/', handler=LoggingHandler),
    webapp2.Route('/image/<key>/', handler=ImageHandler),
    webapp2.Route('/post/<user>/', handler=PostHandler),
    webapp2.Route('/user/<user>/<type>/',handler=UserHandler),
    webapp2.Route('/image/<key>/delete/',handler=DeleteHandler),
    webapp2.Route('/user/authenticate/',handler=AuthHandler),
    ],
    debug=True)
