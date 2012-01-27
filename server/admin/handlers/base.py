#from collections import defaultdict
#from pymongo.objectid import InvalidId, ObjectId
#import re
import datetime
#import urllib
import tornado.web
#from tornado.escape import json_decode, json_encode
from tornado_utils.routes import route
from core.handlers import BaseHandler as CoreBaseHandler


class djangolike_request_dict(dict):
    def getlist(self, key):
        return self.get(key)


class BaseHandler(CoreBaseHandler):

    def render(self, template, **options):
        options['current_url'] = self.request.path
        return super(BaseHandler, self).render(template, **options)


class AuthenticatedBaseHandler(BaseHandler):
    MAYOR_OK = True

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.redirect('/#login')
        elif not user['superuser']:
            # check that you're ambassador or mayor
            if (self.db.Ambassador
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

        user = self.get_current_user()
        is_superuser = is_ambassador = False
        if user['superuser']:
            is_superuser = True
        elif (self.db.Ambassador
                .find({'user': user['_id']})
                .count()):
            is_ambassador = True
        options['is_superuser'] = is_superuser
        options['is_ambassador'] = is_ambassador

        self.render('admin/home.html', **options)
