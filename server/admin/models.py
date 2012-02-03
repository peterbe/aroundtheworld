from pymongo.objectid import ObjectId
from core.models import BaseDocument, register


@register
class FlashMessage(BaseDocument):
    __collection__ = 'flash_messages'
    structure = {
      'user': ObjectId,
      'title': unicode,
      'text': unicode,
      'type': unicode,
      'read': bool,
    }
    default_values = {
      'read': False,
      'text': u'',
      'type': 'info',
    }
    required_fields = ['user', 'title']
    validators = {
      'type': lambda x: x in ('info', 'error', 'success')
    }

    @property
    def user(self):
        return self.db.User.find_one({'_id': self['user']})
