import cgi
import datetime
import urllib
import webapp2
import json
import logging
import urlparse
# from webapp2_extras import sessions

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.api import images

from models import *


################################################################################
"""The home page of the app"""
class HomeHandler(webapp2.RequestHandler):

    """Show the webform when the user is on the home page"""
    def get(self):
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


        self.response.out.write("""
        <form action="/post/default/" enctype="multipart/form-data" method="post">
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
        </html>""")


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
                #ancestor_key = ndb.Key("User", user)
                #photos = Photo.query_user(ancestor_key).fetch(100)
                photos = self.get_data(user)
                if type == "json":
                    output = self.json_results(photos)
                else:
                    output = self.web_results(photos)
                self.response.out.write(output)
            else: 
                self.response.out.write("401 No Authorization \r\n") 
                self.response.set_status(401)
        else: 
            self.response.out.write("401 No Authorization \r\n") 
            self.response.set_status(401)

    def json_results(self,photos):
        """Return formatted json from the datastore query"""
        json_array = []
        for photo in photos:
            dict = {}
            dict['image_url'] = "image/" + photo.key.urlsafe() + "/?id_token=" + self.request.cookies.get("id_token")
            dict['caption'] = photo.caption
            dict['date'] = str(photo.date)
            json_array.append(dict)
        return json.dumps({'results' : json_array})

    def web_results(self,photos):
        """Return html formatted json from the datastore query"""
        html = ""
        for photo in photos:
            html += '<div><hr><div><img src="/image/%s/" width="200" border="1"/></div>' % photo.key.urlsafe()
            html += '<div><blockquote>Caption: %s<br>User: %s<br>Date:%s</blockquote></div></div>' % (cgi.escape(photo.caption),photo.user,str(photo.date))
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
        # user = User.query(User.username == photo.key.parent()).get()
        # id_token = self.request.cookies.get("id_token")
        # if id_token == None:
        #     self.response.out.write('401 No Authorization. You need to authenticate again. ')
        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)

        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_photo_user(key, id_token):
                if photo.image:
                    self.response.headers['Content-Type'] = 'image/png'
                    self.response.out.write(photo.image)
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

        # If we are submitting from the web form, we will be passing
        # the user from the textbox.  If the post is coming from the
        # API then the username will be embedded in the URL
        if self.request.get('user'):
            user = self.request.get('user')

        # Be nice to our quotas
        thumbnail = images.resize(self.request.get('image'), 30,30)

        # Create and add a new Photo entity
        #
        # We set a parent key on the 'Photos' to ensure that they are all
        # in the same entity group. Queries across the single entity group
        # will be consistent. However, the write rate should be limited to
        # ~1/second.
        photo = Photo(parent=ndb.Key("User", user),
                # user=user,
                caption=self.request.get('caption'),
                image=thumbnail)
        photo_key = photo.put()

        # Store the image into Google Cloud Storage


        # Store the image key into the corresponding user entity
        the_user = User.query(User.username == user).get()
        the_user.photos.append(photo_key)
        the_user.put()

        # Clear the cache (the cached version is going to be outdated)
        key = user + "_photos"
        memcache.delete(key)

        # Redirect to print out JSON
        self.redirect('/user/%s/json/' % user)


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

    def post(self, key):

        photo_key = ndb.Key(urlsafe=key)

        url = self.request.url
        parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(parsed.query)

        if 'id_token' in query:
            id_token = query['id_token'][0]
            if User.auth_photo_user(key, id_token):
                
                # Delete from storage


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

app = webapp2.WSGIApplication([
    ('/', HomeHandler),
    webapp2.Route('/logging/', handler=LoggingHandler),
    webapp2.Route('/image/<key>/', handler=ImageHandler),
    webapp2.Route('/post/<user>/', handler=PostHandler),
    webapp2.Route('/user/<user>/<type>/',handler=UserHandler),
    webapp2.Route('/image/<key>/delete/',handler=DeleteHandler),
    webapp2.Route('/user/authenticate/',handler=AuthHandler),
    ],
    debug=True)
