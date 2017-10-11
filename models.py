from google.appengine.ext import ndb

class Photo(ndb.Model):
    """Models a user uploaded photo entry"""

    # user = ndb.StringProperty()
    # image = ndb.BlobProperty()
    b_key = ndb.StringProperty()
    caption = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def query_user(cls, ancestor_key):
        """Return all photos for a given user"""
        return cls.query(ancestor=ancestor_key).order(-cls.date)

    @classmethod
    def query_user_alternate(cls, ancestor_key):
        """Return all photos for a given user using the gql syntax.
        It returns the same as the above method.
        """
        return ndb.gql('SELECT * '
                        'FROM Photo '
                        'WHERE ANCESTOR IS :1 '
                        'ORDER BY date DESC LIMIT 10',
                        ancestor_key)

class User(ndb.Model):
    """Models a user"""

    name = ndb.StringProperty()
    email = ndb.StringProperty()
    # unique_id = ndb.StringProperty()
    photos = ndb.KeyProperty(kind='Photo', repeated=True)
    username = ndb.StringProperty()
    password = ndb.StringProperty()
    # id_token = ndb.StringProperty()

    @classmethod
    def delete_photo(cls, photo_key, id_token):
        """Delete photo for a given user"""
        user = ndb.Key(urlsafe=id_token).get()
        photos = user.photos
        for photo in photos:
            if photo.urlsafe() == photo_key.urlsafe():
                photos.remove(photo)
        user.photos = photos
        user.put()

    @classmethod
    def auth_photo_user(cls, photo_key, id_token):
        """Return if the user owes the photo"""
        photos = ndb.Key(urlsafe=id_token).get().photos
        for photo in photos:
            if photo.urlsafe() == photo_key:
                return True
        return False

    @classmethod
    def auth_user(cls, username, id_token):
        if ndb.Key(urlsafe=id_token).get():
            user = ndb.Key(urlsafe=id_token).get()
            if user.username == username:
                return True
            else: 
                return False
        else:
            return False
        

