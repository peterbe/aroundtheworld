import re
import datetime
import random
import os
import logging
import time
from pprint import pprint, pformat
import tornado.auth
import tornado.web
import tornado.gen
from tornado.web import HTTPError
from tornado_utils.routes import route
from tornado_utils.send_mail import send_email
from tornado.escape import json_decode, json_encode
from pymongo.objectid import InvalidId, ObjectId
from geopy.distance import distance as geopy_distance

from models import User
import settings


class BaseHandler(tornado.web.RequestHandler):

    def write_json(self, struct, javascript=False):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(tornado.escape.json_encode(struct))

    def write_jsonp(self, callback, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write('%s(%s)' % (callback, tornado.escape.json_encode(struct)))


    def get_current_user(self):
        _id = self.get_secure_cookie('user')
        if _id:
            try:
                return self.db.User.find_one({'_id': ObjectId(_id)})
            except InvalidId:  # pragma: no cover
                return self.db.User.find_one({'username': _id})

    def get_user_settings(self, user, fast=False):
        return self.get_current_user_settings(user=user, fast=fast)

    # shortcut where the user parameter is not optional
    def get_current_user_settings(self,
                                  user=None,
                                  fast=False,
                                  create_if_necessary=False):
        if user is None:
            user = self.get_current_user()

        if not user:
            raise ValueError("Can't get settings when there is no user")
        _search = {'user': user['_id']}
        if fast:
            return self.db.UserSettings.collection.find_one(_search) # skip mongokit
        else:
            user_settings = self.db.UserSettings.find_one(_search)
            if create_if_necessary and not user_settings:
                user_settings = self.db.UserSettings()
                user_settings['user'] = user['_id']
                user_settings.save()
            return user_settings

    def create_user_settings(self, user, **default_settings):
        user_settings = self.db.UserSettings()
        user_settings.user = user['_id']
        for key in default_settings:
            setattr(user_settings, key, default_settings[key])
        user_settings.save()
        return user_settings

    def get_current_location(self, user=None):
        if user is None:
            user = self.get_current_user()
        if user:
            if user['current_location']:
                return (self.db.Location
                        .find_one({'_id': user['current_location']}))

    def get_state(self):
        """what state of play the user is in"""
        state = {}
        user = self.get_current_user()
        if user:
            state['user'] = {}
            state['user']['name'] = user.get_full_name()
            state['user']['miles_total'] = 12345
            state['user']['coins_total'] = 325
            location = self.get_current_location(user)
            if location:
                state['location'] = {
                  'id': str(location['_id']),
                  'code': location['code'],
                  'city': location['city'],
                  'locality': location['locality'],
                  'country': location['country'],
                  'name': unicode(location),
                }
            else:
                state['location'] = None
        else:
            state['user'] = None
        return state

    @property
    def redis(self):
        return self.application.redis

    @property
    def db(self):
        return self.application.db

    def write_error(self, status_code, **kwargs):
        if status_code >= 500 and not self.application.settings['debug']:
            if self.application.settings['admin_emails']:
                try:
                    self._email_exception(status_code, *kwargs['exc_info'])
                except:
                    logging.error("Failing to email exception", exc_info=True)
            else:
                logging.warn("No ADMIN_EMAILS set up in settings to "
                             "email exception")
        if self.application.settings['debug']:
            super(BaseHandler, self).write_error(status_code, **kwargs)
        else:
            options = dict(
              status_code=status_code,
              err_type=kwargs['exc_info'][0],
              err_value=kwargs['exc_info'][1],
              err_traceback=kwargs['exc_info'][2],
            )
            self.render("error.html", **options)

    def _email_exception(self, status_code, err_type, err_val, err_traceback):
        import traceback
        from cStringIO import StringIO
        from pprint import pprint
        out = StringIO()
        subject = "%r on %s" % (err_val, self.request.path)
        out.write("TRACEBACK:\n")
        traceback.print_exception(err_type, err_val, err_traceback, 500, out)
        traceback_formatted = out.getvalue()
        #print traceback_formatted
        out.write("\nREQUEST ARGUMENTS:\n")
        arguments = self.request.arguments
        if arguments.get('password') and arguments['password'][0]:
            password = arguments['password'][0]
            arguments['password'] = password[:2] + '*' * (len(password) -2)
        pprint(arguments, out)
        out.write("\nCOOKIES:\n")
        for cookie in self.cookies:
            out.write("\t%s: " % cookie)
            out.write("%r\n" % self.get_secure_cookie(cookie))

        out.write("\nREQUEST:\n")
        for key in ('full_url', 'protocol', 'query', 'remote_ip',
                    'request_time', 'uri', 'version'):
            out.write("  %s: " % key)
            value = getattr(self.request, key)
            if callable(value):
                try:
                    value = value()
                except:
                    pass
            out.write("%r\n" % value)

        out.write("\nHEADERS:\n")
        pprint(dict(self.request.headers), out)
        try:
            send_email(self.application.settings['email_backend'],
                   subject,
                   out.getvalue(),
                   self.application.settings['admin_emails'][0],
                   self.application.settings['admin_emails'],
                   )
        except:
            logging.error("Failed to send email",
                          exc_info=True)

    def render(self, template, **options):
        if not options.get('page_title'):
            options['page_title'] = settings.PROJECT_TITLE
        return super(BaseHandler, self).render(template, **options)



@route('/')
class HomeHandler(BaseHandler):

    def render(self, template, **options):
        options['javascript_test_file'] = self.get_argument('test', None)
        options['state'] = self.get_state()
        #options['state_json'] = tornado.escape.json_encode(self.get_state())
        return super(HomeHandler, self).render(template, **options)

    def get(self):
        options = {}

        self.render('home.html', **options)

@route('/offline/')
class OfflineHomeHandler(HomeHandler):

    def get(self):
        options = {}
        self.render('offline.html', **options)

@route('/flightpaths/')
class FlightPathsHandler(BaseHandler):

    def check_xsrf_cookie(self):
        pass

    def get(self):
        data = [{u'to': [35.772095999999998, -78.638614500000017],
                 u'from': [37.774929499999999, -122.41941550000001]}]
        self.write_json(data)

    def post(self):
        print repr(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        print data
        self.write_json({'status': 'OK'})


@route('/quizzing.json$', name='quizzing_json')
class QuizzingHandler(BaseHandler):

    def get(self):
        user = self.get_current_user()
        location = self.get_current_location(user)
        data = {}
        data['quiz_name'] = 'Mathematics Professor!'
        question = self._get_next_question(user, location)
        if not question['alternatives_sorted']:
            random.shuffle(question['alternatives'])

        data['question'] = {
          'id': str(question['_id']),
          'text': question['text'],
          'alternatives': question['alternatives'],
        }
        data['question']['seconds'] = 10
        self.write_json(data)

    def _get_next_question(self, user, location, allow_repeats=False):
        filter_ = {'location': location['_id']}
        if not allow_repeats:
            session = (self.db.QuestionSession
                       .find_one({'user': user['_id'],
                                  'location': location['_id'],
                                  'finish_date': {'$ne': None}}))
            if session is None:
                session = self.db.QuestionSession()
                session['user'] = user['_id']
                session['location'] = location['_id']
                session.save()
            past_question_ids = set()
            for sq in (self.db.SessionQuestions
                       .find({'session': session['_id']})):
                past_question_ids.add(sq['question'])
            if past_question_ids:
                filter_['_id'] = {'$nin': past_question_ids}

        questions = self.db.Question.find(filter_)
        count = questions.count()
        if not count:
            if allow_repeats:
                raise RunTimeError("Not enough questions")
            return self._get_next_question(user, location, allow_repeats=True)

        nth = random.randint(0, count - 1)
        for question in questions.limit(1).skip(nth):
            return question

    def post(self):
        answer = self.get_argument('answer')
        question_id = self.get_argument('id')
        question = self.db.Question.find_one({'_id': ObjectId(question_id)})
        data = {}
        data['correct'] = question.check_answer(answer)
        if not data['correct']:
            data['correct_answer'] = question['correct']
        data['points_value'] = question.get('points_value', 1)
        self.write_json(data)


@route('/miles.json$', name='miles_json')
class MilesHandler(BaseHandler):

    def get(self):
        user = self.get_current_user()
        miles = 12456
        data = {}
        data['miles_friendly'] = _commafy(miles)
        data['percentage'] = '4%'
        self.write_json(data)

def _commafy(s):
    r = []
    for i, c in enumerate(reversed(str(s))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)


@route('/location.json$', name='location')
class LocationHandler(BaseHandler):

    def get(self):
        locations = []
        for location in self.db.Location.find().sort('city', 1):
            locations.append({'name': unicode(location),
                              'id': str(location['_id'])})
        self.write_json({'locations': locations})

    def post(self):
        _id = self.get_argument('id')
        user = self.get_current_user()
        location = self.db.Location.find_one({'_id': ObjectId(_id)})
        user['current_location'] = location['_id']
        user.save()
        data = {}
        data['location'] = {
          'id': str(location['_id']),
          'name': unicode(location)
        }
        self.write_json({'state': data})


@route('/city.json$', name='city')
class CityHandler(BaseHandler):

    def get(self):
        data = {}
        search = self.get_argument('search')
        if len(search) == 24:
            location = self.db.Location.find_one({'_id': ObjectId(search)})
        elif len(search) == 3:
            location = self.db.Location.find_one({'code': search.upper()})
        else:
            raise NotImplementedError
        if not location:
            raise tornado.web.HTTPError(404, search)
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        if location != current_location:
            self.write_json({
              'wrong_city': True,
              'current_city': current_location['code'],
            })
            return

        data['name'] = unicode(location)
        data['city'] = location['city']
        data['locality'] = location['locality']
        data['country'] = location['country']

        self.write_json(data)


@route('/airport.json$', name='airport')
class AirportHandler(BaseHandler):

    def get(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        data = {
          'airport_name': current_location['airport_name'],
        }
        destinations = []
        user_settings = self.get_current_user_settings(user)
        for location in (self.db.Location
                          .find({'_id': {'$ne': current_location['_id']}})):
            distance = self.calculate_distance(current_location, location)
            price = self.calculate_price(distance.miles, user)
            if user_settings['kilometers']:
                distance_friendly = '%d km' % distance.kilometers
            else:
                distance_friendly = '%d miles' % distance.miles
            destination = {
              'code': location['code'],
              'name': unicode(location),
              'city': location['city'],
              'locality': location['locality'],
              'country': location['country'],
              'price': price,
              'miles': distance.miles,
              'distance': distance_friendly,
            }
            destinations.append(destination)

        data['destinations'] = destinations
        self.write_json(data)

    def calculate_price(self, miles, user):
        return int(round(miles * .1))

    def calculate_distance(self, from_location, to_location):
        from_ = (from_location['lat'], from_location['lng'])
        to = (to_location['lat'], to_location['lng'])
        return geopy_distance(from_, to)



@route('/state.(json|html)$', name='state')
class StateHandler(BaseHandler):

    def get(self, format):
        state = self.get_state()
        L,= self.db.Location.find().limit(1)
        state['location'] ={
        'id':str(L['_id']),'city':L['city'], 'locality':L['locality'],'country':L['country']
        }
        if format == 'html':
            self.render('div.usernav.html', state=state)
        else:
            self.write_json({'state': state})


class BaseAuthHandler(BaseHandler):

    def get_next_url(self, default='/'):
        next = default
        if self.get_argument('next', None):
            next = self.get_argument('next')
        elif self.get_cookie('next', None):
            next = self.get_cookie('next')
            self.clear_cookie('next')
        return next

    def notify_about_new_user(self, user, extra_message=None):
        #return # temporarily commented out
        if self.application.settings['debug']:
            return

        try:
            self._notify_about_new_user(user, extra_message=extra_message)
        except:
            # I hate to have to do this but I don't want to make STMP errors
            # stand in the way of getting signed up
            logging.error("Unable to notify about new user", exc_info=True)

    def _notify_about_new_user(self, user, extra_message=None):
        subject = "New user!"
        email_body = "%s %s\n" % (user.first_name, user.last_name)
        email_body += "%s\n" % user.email
        if extra_message:
            email_body += '%s\n' % extra_message

        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['webmaster'],
                   self.application.settings['admin_emails'],
                   )

    def make_username(self, first_name, last_name):
        def simple(s):
            return s.lower().replace(' ','').replace('-','')
        return '%s%s' % (simple(first_name), simple(last_name))

    def post_login_successful(self, user):
        """executed by the Google, Twitter and Facebook authentication handlers"""
        return


@route('/auth/google/', name='auth_google')
class GoogleAuthHandler(BaseAuthHandler, tornado.auth.GoogleMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("openid.mode", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        if self.get_argument('next', None):
            # because this is going to get lost when we get back from Google
            # stick it in a cookie
            self.set_cookie('next', self.get_argument('next'))
        self.authenticate_redirect()

    def _on_auth(self, user):
        if not user:
            raise HTTPError(500, "Google auth failed")
        if not user.get('email'):
            raise HTTPError(500, "No email provided")

        user_struct = user
        locale = user.get('locale') # not sure what to do with this yet
        first_name = user.get('first_name')
        last_name = user.get('last_name')
        username = user.get('username')
        email = user['email']
        if not username:
            username = email.split('@')[0]

        user = self.db.User.one(dict(username=username))
        if not user:
            user = self.db.User.one(dict(email=email))
            if user is None:
                user = self.db.User.one(dict(email=re.compile(re.escape(email), re.I)))

        if not user:
            # create a new account
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            import uuid
            user.set_password(unicode(uuid.uuid4()))
            user.save()

            self.notify_about_new_user(user, extra_message="Used Google OpenID")

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.google = user_struct
        if user.email:
            user_settings.email_verified = user.email
        user_settings.save()

        self.post_login_successful(user)
        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route(r'/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())


# this handler gets automatically appended last to all handlers inside app.py
class PageNotFoundHandler(BaseHandler):

    def get(self):
        path = self.request.path
        if not path.endswith('/'):
            new_url = '%s/' % path
            if self.request.query:
                new_url += '?%s' % self.request.query
            self.redirect(new_url)
            return
        raise HTTPError(404, path)
