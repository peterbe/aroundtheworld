import re
from pymongo.objectid import ObjectId
import datetime
from mongokit import Document
from mongokit import Connection
import markdown


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
      'current_location': ObjectId,
      'superuser': bool
    }

    use_autorefs = False
    required_fields = ['username']
    default_values = {
      'superuser': False
    }

    def __unicode__(self):
        return self.username

    def get_full_name(self):
        name = ('%s %s' % (self['first_name'], self['last_name'])).strip()
        if not name:
            name = self['username']
        return name

    def set_password(self, raw_password, encrypt=False):
        if encrypt:
            from tornado_utils import encrypt_password
            raw_password = encrypt_password(raw_password)
        self.password = raw_password

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
            raise NotImplementedError("Not checking clear text passwords")

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


@register
class Ambassador(BaseDocument):
    __collection__ = 'ambassadors'
    structure = {
      'user': ObjectId,
      'country': unicode,
    }


@register
class Mayor(BaseDocument):
    __collection__ = 'mayors'
    structure = {
      'user': ObjectId,
      'location': ObjectId,
    }


@register
class UserSettings(BaseDocument):
    __collection__ = 'usersettings'
    structure = {
      'user': ObjectId,
      'kilometers': bool,
      'coins_total': int,
      'miles_total': float,
      'google': dict,
      'disable_sound': bool,
    }

    required_fields = ['user']
    default_values = {
      'kilometers': False,
      'coins_total': 0,
      'miles_total': 0.0,
      'disable_sound': False,
    }


@register
class Location(BaseDocument):
    __collection__ = 'locations'
    structure = {
      'city': unicode,
      'country': unicode,
      'locality': unicode,  # e.g. US states
      'code': unicode,
      'airport_name': unicode,
      'lat': float,
      'lng': float,
    }

    required_fields = [
      'city',
      'country',
      'lat',
      'lng',
      ]

    def __unicode__(self):
        name = self['city']
        if self['locality']:
            name += ', %s' % self['locality']
        name += ', %s' % self['country']
        return name

    def __str__(self):
        return str(unicode(self))

    def dictify(self):
        return {
          'name': unicode(self),
          'code': self['code'],
          'airport_name': self['airport_name'],
          'city': self['city'],
          'locality': self['locality'],
          'country': self['country'],
          'lat': self['lat'],
          'lng': self['lng'],
        }


@register
class Flight(BaseDocument):
    __collection__ = 'flights'
    structure = {
      'user': ObjectId,
      'from': ObjectId,
      'to': ObjectId,
      'miles': float,
    }
    required_fields = structure.keys()


@register
class Transaction(BaseDocument):
    __collection__ = 'transactions'
    structure = {
      'user': ObjectId,
      'cost': int,
      'flight': ObjectId,
    }
    required_fields = ['user', 'cost']


@register
class Job(BaseDocument):
    __collection__ = 'earnings'
    structure = {
      'user': ObjectId,
      'coins': int,
      'category': ObjectId,
      'location': ObjectId,
    }


@register
class Question(BaseDocument):
    __collection__ = 'questions'
    structure = {
      'text': unicode,
      'correct': unicode,
      'alternatives': [unicode],
      'alternatives_sorted': bool,
      'author': ObjectId,
      'points_value': int,
      'location': ObjectId,
      'category': ObjectId,
      'published': bool,
      'notes': unicode,
      'didyouknow': unicode,
    }

    default_values = {
      'alternatives_sorted': False,
      'points_value': 1,
      'published': True,
    }

    HIGHEST_POINTS_VALUE = 5

    def check_answer(self, value):
        return value.lower() == self['correct'].lower()

    def has_picture(self):
        return bool(self.db.QuestionPicture
                    .find({'question': self['_id']})
                    .count())

    def get_picture(self):
        return self.db.QuestionPicture.find_one({'question': self['_id']})


@register
class QuestionPicture(BaseDocument):
    __collection__ = 'question_pictures'
    structure = {
      'question': ObjectId,
      'render_attributes': dict,
    }
    required_fields = ['question']
    gridfs = {'files': ['original']}


@register
class Category(BaseDocument):
    __collection__ = 'questioncategories'
    structure = {
      'name': unicode,
      'description': unicode,
      'manmade': bool,
    }

    required_fields = ['name']

    default_values = {
      'manmade': False,
    }

    def __unicode__(self):
        return self['name']

    def __str__(self):
        return str(unicode(self))





@register
class QuestionSession(BaseDocument):
    __collection__ = 'questionsessions'
    structure = {
      'user': ObjectId,
      'location': ObjectId,
      'category': ObjectId,
      'finish_date': datetime.datetime,
      'start_date': datetime.datetime,
    }

    default_values = {
      'start_date': datetime.datetime.utcnow,
    }


@register
class SessionAnswer(BaseDocument):
    __collection__ = 'sessionquestions'
    structure = {
      'session': ObjectId,
      'question': ObjectId,
      'answer': unicode,
      'correct': bool,
      'time': float,
      'points': int,
      'timedout': bool,
    }

    required_fields = [
      'question',
      'session',
    ]


@register
class PinpointCenter(BaseDocument):
    __collection__ = 'pinpointcenters'
    structure = {
      'country': unicode,
      'south_west': [float],
      'north_east': [float],
    }

    required_fields = structure.keys()


@register
class PinpointSession(BaseDocument):
    __collection__ = 'pintpointsessions'
    structure = {
      'center': ObjectId,
      'user': ObjectId,
      'finish_date': datetime.datetime,
    }

    required_fields = ['center', 'user']


@register
class PinpointAnswer(BaseDocument):
    __collection__ = 'pinpointanswer'
    structure = {
      'session': ObjectId,
      'location': ObjectId,
      'answer': [float],
      'time': float,
      'points': float,
      'miles': float,
      'timedout': bool,
    }

    required_fields = [
      'session',
      'location',
    ]


@register
class HTMLDocument(BaseDocument):
    __collection__ = 'htmldocuments'
    structure = {
      'html': unicode,
      'source': unicode,
      'source_format': unicode,
      'type': unicode,
      'location': ObjectId,
      'country': unicode,
      'user': ObjectId,
      'category': ObjectId,
      'notes': unicode,
    }

    required_fields = [
      'source',
      'source_format',
      'type',
    ]

    default_values = {
      'source_format': u'html',
    }

    validators = {
      'source_format': lambda x: x in ('html', 'markdown'),
      'type': lambda x: x in ('intro', 'ambassadors')
    }

    def update_html(self):
        if self['source_format'] == 'markdown':
            self['html'] = markdown.markdown(self['source'])
            self.save()
        else:
            raise NotImplementedError(self['source_format'])


@register
class Feedback(BaseDocument):
    __collection__ = 'feedback'
    structure = {
      'what': unicode,
      'comment': unicode,
      'user': ObjectId,
      'location': ObjectId,
    }

    required_fields = ['what', 'comment']
