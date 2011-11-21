import re
from hashlib import md5
import uuid
from pymongo.objectid import ObjectId
import datetime
from mongokit import Document, ValidationError
from tornado_utils import encrypt_password

from mongokit import Connection
connection = Connection()
def register(cls):
    connection.register([cls])
    return cls

class BaseDocument(Document):
    structure = {
      'add_date': datetime.datetime,
      'modify_date': datetime.datetime,
    }

    default_values = {
      'add_date': datetime.datetime.utcnow,
      'modify_date': datetime.datetime.utcnow
    }
    use_autorefs = False
    use_dot_notation = True

    def save(self, *args, **kwargs):
        if '_id' in self and kwargs.get('update_modify_date', True):
            self.modify_date = datetime.datetime.utcnow()
        super(BaseDocument, self).save(*args, **kwargs)

    def __eq__(self, other_doc):
        try:
            return self._id == other_doc._id
        except AttributeError:
            return False

    def __ne__(self, other_doc):
        return not self == other_doc


@register
class User(BaseDocument):
    __collection__ = 'users'
    structure = {
      'username': unicode,
      'email': unicode,
      'password': unicode,
      'first_name': unicode,
      'last_name': unicode,
    }

    use_autorefs = False
    required_fields = ['username']
    default_values = {
    }

    def __unicode__(self):
        return self.username

    def set_password(self, raw_password):
        self.password = encrypt_password(raw_password)

    def check_password(self, raw_password):
        """
        Returns a boolean of whether the raw_password was correct. Handles
        encryption formats behind the scenes.
        """
        if '$bcrypt$' in self.password:
            import bcrypt
            hashed = self.password.split('$bcrypt$')[-1].encode('utf8')
            return hashed == bcrypt.hashpw(raw_password, hashed)
        else:
            raise NotImplementedError("No checking clear text passwords")

    def delete(self):
        try:
            for us in (self.db.UserSettings
                       .find({'user': self['_id']})):
                us.delete()
        finally:
            super(User, self).delete()

    def find_by_username(self, username):
        return self._find_by_key('username', username)

    def find_by_email(self, email):
        return self._find_by_key('email', email)

    def _find_by_key(self, key, value):
        user = self.db.User.one({key: value})
        if not user:
            user = self.db.User.one({key:
              re.compile(re.escape(value), re.I)})
        return user
