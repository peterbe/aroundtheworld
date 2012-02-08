#from collections import defaultdict
#from pymongo.objectid import InvalidId, ObjectId
#import re
import time
import urllib
from pprint import pprint
import datetime
#import urllib
import tornado.web
#from tornado.escape import json_decode, json_encode
from tornado_utils.routes import route
from core.handlers import BaseHandler as CoreBaseHandler
from tornado_utils.timesince import smartertimesince
from admin.utils import truncate_text


class djangolike_request_dict(dict):
    def getlist(self, key):
        return self.get(key)


class BaseHandler(CoreBaseHandler):

    def render(self, template, **options):
        options['current_url'] = self.request.path
        user = self.get_current_user()
        options['is_mayor'] = options['is_ambassador'] = False
        options['is_superuser'] = user['superuser']
        if not options['is_superuser']:
            options['is_ambassador'] = (self.db.Ambassador
                                        .find({'user': user['_id']})
                                        .count())
        options['messages'] = self.pull_flash_messages()
        return super(BaseHandler, self).render(template, **options)

    def push_flash_message(self, title, text=u'', user=None,
                           type_='info'  # 'success' or 'error'
                           ):
        if user is None:
            user = self.get_current_user()
            assert user
            #if not user:
            #    return
        if not text:
            raise ValueError(
               "AT the moment we can't accept blank texts on flash "\
               "messages because gritter won't be able to show it")
        for msg in (self.db.FlashMessage
                    .find({'user': user['_id']})
                    .sort('add_date', -1)
                    .limit(1)):
            if msg['title'] == title and msg['text'] == text:
                # but was it several seconds ago?
                if (datetime.datetime.utcnow() - msg['add_date']).seconds < 3:
                    return
        msg = self.db.FlashMessage()
        msg['user'] = user['_id']
        msg['title'] = unicode(title)
        msg['text'] = unicode(text)
        msg['type'] = unicode(type_)
        msg.save()

    def pull_flash_messages(self, unread=True, user=None):
        if user is None:
            user = self.get_current_user()
            assert user
            #if not user:
            #    return []
        _search = {'user': user['_id']}
        if unread:
            _search['read'] = False
        messages = []
        for message in self.db.FlashMessage.find(_search).sort('add_date', 1):
            messages.append(message)
            message['read'] = True
            message.save()
        return messages


class AuthenticatedBaseHandler(BaseHandler):
    MAYOR_OK = True
    AMBASSADOR_OK = True

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.redirect('/#login')
        elif not user['superuser']:
            # check that you're ambassador or mayor
            if self.AMBASSADOR_OK and (self.db.Ambassador
                                       .find({'user': user['_id']})
                                       .count()):
                return
            if self.MAYOR_OK and (self.db.Mayor
                                  .find({'user': user['_id']})
                                  .count()):
                return
            self.redirect(self.reverse_url('admin_ohno'))


class AmbassadorBaseHandler(AuthenticatedBaseHandler):

    MAYOR_OK = False
    AMBASSADOR_OK = True


class SuperuserBaseHandler(AuthenticatedBaseHandler):

    MAYOR_OK = False
    AMBASSADOR_OK = False


@route('/admin/ohno/', name='admin_ohno')
class OhNoAdminHandler(BaseHandler):
    def get(self):
        self.render('admin/ohno.html')


@route('/admin/become/', name='admin_become')
class BecomeAdminHandler(BaseHandler):
    def get(self):
        if not self.application.settings['debug']:
            raise tornado.web.HTTPError(403, "not right now")
        search = self.get_argument('search').lower()
        found_user = None
        for user in self.db.User.find():
            if (user['username'].lower().startswith(search) or
                user['email'].lower().startswith(search)):
                if found_user:
                    raise tornado.web.HTTPError(400, "found more than one")
                found_user = user
        if not found_user:
            raise tornado.web.HTTPError(404, "found none")
        self.set_secure_cookie("user", str(found_user['_id']), expires_days=1)

        #self.write('cool\n')
        #self.finish()
        self.redirect(self.reverse_url('admin_home'))


@route('/admin/', name='admin_home')
class HomeAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        options = {}
        options['count_questions_published'] = (
          self.db.Question
           .find({'published': True})
           .count()
        )
        options['count_questions_not_published'] = (
          self.db.Question
           .find({'published': False})
           .count()
        )
        options['count_locations_with_airport_name'] = (
          self.db.Location
          .find({'airport_name': {'$ne': None}})
          .count()
        )
        options['count_locations_total'] = (
          self.db.Location
          .find()
          .count()
        )
        options['count_countries'] = len(
          self.db.Location
          .find().distinct('country')
        )
        options['count_users'] = (
          self.db.User
          .find()
          .count()
        )
        then = datetime.datetime.utcnow() - datetime.timedelta(days=14)
        options['count_new_users'] = (
          self.db.User
          .find({'add_date': {'$gte': then}})
          .count()
        )
        options['count_ambassadors'] = len(
          self.db.Ambassador
          .find().distinct('user')
        )
        options['count_mayors'] = len(
          self.db.Mayor
          .find().distinct('user')
        )

        self.render('admin/home.html', **options)


@route('/admin/news.json', name='admin_news')
class NewsAdminHandler(AuthenticatedBaseHandler):

    MIN_ITEMS = 30
    CUTOFF_DELTA = 60 * 60 * 24
    MAX_ITERATIONS = 5

    def get(self, cutoff_seconds=None, max_date=None, iteration=0):
        items = []
        if cutoff_seconds is None:
            cutoff_seconds = self.CUTOFF_DELTA

        no_items = int(self.get_argument('items', self.MIN_ITEMS))
        now = datetime.datetime.utcnow()
        cutoff = now - datetime.timedelta(seconds=cutoff_seconds)
        filter_ = {'add_date': {'$gt': cutoff}}
        if max_date:
            filter_['add_date']['$lt'] = max_date
        users = self.db.User.find(filter_)
        for model in (self.db.User,
                      self.db.Feedback,
                      self.db.Question,
                      self.db.HTMLDocument):
            objects = model.find(filter_).sort('add_date', -1)
            for item in objects:
                items.append({
                  'summary': self.get_summary(item),
                  'url': self.get_url(item),
                  'ts': time.mktime(item['add_date'].timetuple()),
                  'date': smartertimesince(item['add_date'], now=now),
                })

        items.sort(lambda x,y: cmp(y['ts'], x['ts']))
        if len(items) > no_items:
            items = items[:no_items]

        if len(items) < no_items and iteration < self.MAX_ITERATIONS:
            items.extend(self.get(
              cutoff_seconds=cutoff_seconds + self.CUTOFF_DELTA,
              max_date=cutoff,
              iteration=iteration + 1
            ))

        if max_date is None:
            self.write_json({'items': items})
        else:
            return items

    def get_url(self, item):
        if item.__class__ == self.db.User._obj_class:
            return (self.reverse_url('admin_users') +
                    '?q=%s' % urllib.quote(item['username']))

        if item.__class__ == self.db.Feedback._obj_class:
            return self.reverse_url('admin_feedbacks')

        if item.__class__ == self.db.Question._obj_class:
            return self.reverse_url('admin_question', item['_id'])

        if item.__class__ == self.db.HTMLDocument._obj_class:
            return self.reverse_url('admin_document', item['_id'])

        raise NotImplementedError(item.__class__.__name__)

    def get_summary(self, item):
        if item.__class__ == self.db.Feedback._obj_class:
            comment = item['comment']
            if len(comment) > 40:
                comment = comment[:40].strip() + '...'
            return ("<strong>'%s' feedback!</strong> %s"
                    % (item['what'], comment))

        if item.__class__ == self.db.User._obj_class:
            current_location = (self.db.Location
                                .find_one({'_id': item['current_location']}))
            return ('<strong>User!</strong> %s (currently in %s)' %
                    (item['username'], current_location))

        if item.__class__ == self.db.Question._obj_class:
            category = self.db.Category.find_one({'_id': item['category']})
            text = truncate_text(item['text'], 80)
            text = ("<strong>'%s' question!</strong> %s" %
                    (category['name'], text))
            if item.has_picture():
                text += ' (with picture)'
            return text.strip()

        if item.__class__ == self.db.HTMLDocument._obj_class:
            text = "<strong>'%s' document!</strong> " % item['type']
            if item['user']:
                user = self.db.User.find_one({'_id': item['user']})
                text += 'about user %s ' % user
            if item['location']:
                location = self.db.Location.find_one({'_id': item['location']})
                text += 'about %s ' % location
            if item['category']:
                category = self.db.Category.find_one({'_id': item['category']})
                text += 'for %s ' % category

            return text.strip()
        raise NotImplementedError(item.__class__.__name__)
