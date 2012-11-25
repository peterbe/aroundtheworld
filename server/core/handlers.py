import time
import uuid
import re
import datetime
import random
import os
import logging
import traceback
import mimetypes
import urllib
from collections import defaultdict
from cStringIO import StringIO
from pprint import pprint
from PIL import Image
import tornado.auth
import tornado.web
import tornado.gen
import tornado.httpclient
import markdown
from tornado.web import HTTPError
from tornado_utils.routes import route
from tornado_utils.send_mail import send_email
from tornado_utils.timesince import smartertimesince
from bson.objectid import ObjectId, InvalidId
from geopy.distance import distance as geopy_distance
from core.ui_modules import PictureThumbnailMixin
from models import Question
import settings
from .ui_modules import commafy


ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
FULL_DATE_FMT = '%d %b %Y'
MOBILE_USER_AGENTS = re.compile(
  'android|fennec|ipad|iemobile|iphone|opera (?:mini|mobi)',
  re.I
)

AWARDTYPE_JOB = u'job'
AWARDTYPE_TUTORIAL = u'tutorial'
AWARDTYPE_SIGNIN = u'signin'
AWARDTYPE_10KMILES = u'10k'
AWARDTYPE_50KMILES = u'50k'
AWARDTYPE_100KMILES = u'100k'

TUTORIAL_INTRO = u"""
**This is the tutorial job.**

It's going to be very *easy questions* with extra thinking time added
but later the questions will get a lot harder and you're going to have
to be faster.

Once you complete the questions, you get **paid in coins**.

**Good luck!**
"""


def calculate_distance(from_location, to_location):
    from_ = (from_location['lat'], from_location['lng'])
    to = (to_location['lat'], to_location['lng'])
    return geopy_distance(from_, to)


class NoQuestionsError(RuntimeError):
    pass


class NoLocationsError(RuntimeError):
    pass



class BaseHandler(tornado.web.RequestHandler):

    NOMANSLAND = {
      'city': u'Nomansland',
      'country': u'Tutorialia',
      'airport_name': u'Tutorial International Airport',
      'code': u'000',
      'lat': 29.0,
      'lng': -42.0,
    }

    PLUGINS = {
      'banks': ['css/plugins/banks.css',
                'plugins/banks.js'],
      'login': ['css/plugins/login.css',
                'plugins/login.js'],
      'quizzing': ['css/plugins/quizzing.css',
                   'plugins/quizzing.js'],
      'picturedetective': ['css/plugins/picturedetective.css',
                           'plugins/picturedetective.js'],
      'settings': ['css/plugins/settings.css',
                   'plugins/settings.js'],
      'miles': ['plugins/miles.js'],
      'coins': ['css/plugins/coins.css',
                #'lib/bootstrap-tab.min.js',
                'plugins/coins.js'],
      'welcome': ['css/plugins/welcome.css',
                  'plugins/welcome.js'],
      'city': ['css/plugins/city.css',
               #'lib/bootstrap-carousel.min.js',
               'plugins/city.js'],
      'airport': ['css/plugins/airport.css',
                  'plugins/airport.js'],
      'signout': ['plugins/signout.js'],
      'flying': ['plugins/flying.js'],
      'pinpoint': ['css/plugins/pinpoint.css',
                   'plugins/pinpoint.js'],
      'feedback': ['plugins/feedback.js'],
      'questionwriter': ['//api.filepicker.io/v0/filepicker.js',
                         'css/plugins/questionwriter.css',
                         #'lib/bootstrap-tab.min.js',
                         'plugins/questionwriter.js'],
      'awards': ['css/plugins/awards.css',
                 '//fonts.googleapis.com/css?family=Monsieur+La+Doulaise|Tangerine|Homemade+Apple|UnifrakturMaguntia',
                 'plugins/awards.js'],
      'about': ['css/plugins/about.css',
                'plugins/about.js'],
      'league': ['css/plugins/league.css',
                 'lib/handlebars-1.0.0.beta.6.js',
                 'plugins/league.js'],
      'unsubscribed': ['css/plugins/unsubscribed.css',
                       'plugins/unsubscribed.js'],
      'news': ['css/plugins/news.css',
               'lib/transparency.min.js',
               'plugins/news.js'],
    }

#    def write(self, *a, **k):
#        from time import sleep
#        sleep(1)
#        super(BaseHandler, self).write(*a, **k)

#    def initialize(self):
#        if 'plugins.js' in self.request.path:
#            return
#        key = ('%s %s %s' %
#               (self.request.method, self.request.path, self.request.query)
#               ).strip()
#        if len(key) > 75:
#            key = key[:75 - 3] + '...'
#        try:
#            self.redis.zincrby('hits', key, 1)
#        except:
#            logging.critical("Unable to store %r" % key, exc_info=True)

    def write_json(self, struct, javascript=False):
        import warnings
        warnings.warn("Just use regular self.write()", DeprecationWarning, 2)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(tornado.escape.json_encode(struct))

    def write_jsonp(self, callback, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write('%s(%s)' % (callback, tornado.escape.json_encode(struct)))

    def get_current_ip(self):
        ip = self.request.remote_ip
        if ip == '127.0.0.1':
            logging.warn('remote_ip not known')
            ip = None
            #ip = '64.179.205.74'  # debugging, Hartwell, GA
        return ip

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
            # skip mongokit
            return self.db.UserSettings.collection.find_one(_search)
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
        state = {
          'debug': self.application.settings['debug']
        }
        user = self.get_current_user()
        if user:
            user_settings = self.get_current_user_settings()
            state['user'] = {}

            # legacy
            try:
                user['anonymous']
            except KeyError:
                user['anonymous'] = False
                user.save()

            if user['anonymous']:
                state['user']['name'] = ''
                state['user']['anonymous'] = True
            else:
                state['user']['name'] = user.get_full_name()
                state['user']['anonymous'] = False
            state['user']['miles_total'] = int(user_settings['miles_total'])
            state['user']['coins_total'] = user_settings['coins_total']
            state['user']['disable_sound'] = user_settings['disable_sound']
            count_awards = self.db.Award.find({'user': user['_id']}).count()
            count_awards_unread = self.db.Award.find({'user': user['_id'], 'read': False}).count()
            state['user']['awards'] = {
              'count': count_awards, 'unread': count_awards_unread
            }
            location = self.get_current_location(user)
            if user['superuser'] or (self.db.Ambassador
                                     .find({'user': user['_id']})
                                     .count()):
                state['user']['admin_access'] = True
            else:
                state['user']['admin_access'] = False

            if location:
                state['location'] = {
                  'id': str(location['_id']),
                  'code': location['code'],
                  'city': location['city'],
                  'locality': location['locality'],
                  'country': location['country'],
                  'name': unicode(location),
                  'lat': location['lat'],
                  'lng': location['lng'],
                }
                if location['city'] == 'Nomansland':
                    state['location']['nomansland'] = True
            else:
                state['location'] = None
        else:
            state['user'] = None

        invites = self.get_pending_friendship_invites()
        if invites:
            state['invites_pending'] = []
            for token in invites:
                from_user = self.db.User.find_one({
                    '_id': token['user']
                })
                if not from_user:
                    continue
                state['invites_pending'].append({
                    'from': self.get_name(from_user)
                })

        return state

    def get_pending_friendship_invites(self):
        invites = self.get_secure_cookie('invites')
        if invites is None:
            return []
        tokens = []
        for token_str in invites.split('|'):
            token = self.db.FriendshipToken.find_one({'token': token_str})
            if token:
                tokens.append(token)
        return tokens

    def get_name(self, user):
        name = user['username']
        if user['first_name'] or user['last_name']:
            name = ('%s %s' % (
                user['first_name'] or '',
                user['last_name'] or ''
            )).strip()
        if not name:
            name = user['email']
        return name

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
            tb = StringIO()
            traceback.print_exception(
              kwargs['exc_info'][0],
              kwargs['exc_info'][1],
              kwargs['exc_info'][2],
              file=tb, limit=1000
            )
            options = dict(
              status_code=status_code,
              err_type=kwargs['exc_info'][0],
              err_value=kwargs['exc_info'][1],
              err_traceback=tb.getvalue(),
              page_title=settings.PROJECT_TITLE,
            )

            self.render("error.html", **options)

    def _email_exception(self, status_code, err_type, err_val, err_traceback):
        out = StringIO()
        subject = "%r on %s" % (err_val, self.request.path)
        out.write("TRACEBACK:\n")
        traceback.print_exception(err_type, err_val, err_traceback, 500, out)
        #traceback_formatted = out.getvalue()
        #print traceback_formatted
        out.write("\nREQUEST ARGUMENTS:\n")
        arguments = self.request.arguments
        if arguments.get('password') and arguments['password'][0]:
            password = arguments['password'][0]
            arguments['password'] = password[:2] + '*' * (len(password) - 2)
        pprint(arguments, out)
        out.write("\nCOOKIES:\n")
        for cookie in self.cookies:
            out.write("\t%s: " % cookie)
            out.write("%r\n" % self.get_secure_cookie(cookie))

        try:
            current_user = self.get_current_user()
            if current_user:
                out.write("\nUSER:\n")
                out.write("\tusername: %s " % current_user['username'])
                out.write("\temail: %s " % current_user['email'])
        except:
            logging.error("Unable to debug current user", exc_info=True)

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
        options['debug'] = self.application.settings['debug']
        return super(BaseHandler, self).render(template, **options)

    def render_string(self, template, **options):
        options['PROJECT_TITLE'] = settings.PROJECT_TITLE
        options['SIGNATURE'] = settings.SIGNATURE
        output = super(BaseHandler, self).render_string(template, **options)
        output = output.replace('{!{', '{{')  # handlebars
        return output

    def static_url(self, path, **kwargs):
        if self.application.settings['embed_static_url_timestamp']:
            ui_module = self.application.ui_modules['StaticURL'](self)
            try:
                return ui_module.render(path, **kwargs)
            except OSError:
                logging.debug("%r does not exist" % path)
        return super(BaseHandler, self).static_url(path)

    def get_cdn_prefix(self):
        """return something that can be put in front of the static filename
        E.g. if filename is '/static/image.png' and you return
        '//cloudfront.com' then final URL presented in the template becomes
        '//cloudfront.com/static/image.png'
        """
        return self.application.settings.get('cdn_prefix')

    def enough_questions(self, location):
        qs = defaultdict(int)
        search = {'location': location['_id'], 'published': True}
        for q in self.db.Question.find(search, ('category',)):
            qs[q['category']] += 1

        min_ = QuizzingHandler.NO_QUESTIONS
        for count in qs.values():
            if count >= min_:
                return True

        return False

    ## Total earned stuff

    def get_total_earned(self, user_id, only_coins=False):
        if not isinstance(user_id, ObjectId):
            user_id = user_id['_id']

        if only_coins:
            te = (self.db.TotalEarned.collection
                  .find_one({'user': user_id},
                            ('coins',)))
        else:
            te = self.db.TotalEarned.find_one({'user': user_id})
        if not te:
            te = self._set_total_earned(user_id)

        if only_coins:
            return te['coins']

        return te

    def _set_total_earned(self, user_id):
        te = self.db.TotalEarned()
        te['user'] = user_id
        filt = {'user': user_id}
        W = ('coins',)
        for each in self.db.Job.collection.find(filt, W):
            te['coins'] += each['coins']
            te['jobs'] += each['coins']
        for each in self.db.QuestionAnswerEarning.collection.find(filt, W):
            te['coins'] += each['coins']
            te['questions'] += each['coins']
        for each in self.db.Award.collection.find(filt, ('reward',)):
            te['coins'] += each['reward']
            te['awards'] += each['reward']
        for each in self.db.InterestEarning.collection.find(filt, W):
            te['coins'] += each['coins']
            te['interest'] += each['coins']
        te.save()
        return te

    ## Award stuff

    def create_job_award(self, user, location, category, reward, data):
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'%s in %s' % (category, location)
        award['data'] = data
        award['location'] = location['_id']
        award['category'] = category['_id']
        award['type'] = AWARDTYPE_JOB
        award['reward'] = reward
        award.save()
        return award

    def has_job_award(self, user, location, category):
        filter_ = {
          'user': user['_id'],
          'location': location['_id'],
          'category': category['_id'],
          'type': AWARDTYPE_JOB,
        }
        return self.db.Award.find(filter_).count()

    def create_tutorial_award(self, user, reward, data):
        location = self.db.Location.find_one({'code': self.NOMANSLAND['code']})
        category = self.db.Category.find_one({'name': 'Tutorial'})
        data['finishing_tutorial'] = True
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'Finishing the tutorial'
        award['data'] = data
        award['location'] = location['_id']
        award['category'] = category['_id']
        award['type'] = AWARDTYPE_TUTORIAL
        award['reward'] = reward
        award.save()
        return award

    def has_tutorial_award(self, user):
        return (self.db.Award
                .find({'user': user['_id'],
                       'type': AWARDTYPE_TUTORIAL})
                .count())

    def has_signin_award(self, user):
        return (self.db.Award
                .find({'user': user['_id'],
                       'type': AWARDTYPE_SIGNIN})
                .count())

    def has_10k_award(self, user):
        return (self.db.Award
                .find({'user': user['_id'],
                       'type': AWARDTYPE_10KMILES})
                .count())

    def has_50k_award(self, user):
        return (self.db.Award
                .find({'user': user['_id'],
                       'type': AWARDTYPE_50KMILES})
                .count())

    def has_100k_award(self, user):
        return (self.db.Award
                .find({'user': user['_id'],
                       'type': AWARDTYPE_100KMILES})
                .count())

    def create_signin_award(self, user, location, reward, data):
        data['sign_in'] = True
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'Signing in properly'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = AWARDTYPE_SIGNIN
        award['reward'] = reward
        award.save()

    def create_10k_award(self, user, location, reward, data):
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 10,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = AWARDTYPE_10KMILES
        award['reward'] = reward
        award.save()

    def create_50k_award(self, user, location, reward, data):
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 50,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = AWARDTYPE_50KMILES
        award['reward'] = reward
        award.save()

    def create_100k_award(self, user, location, reward, data):
        award = self.db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 100,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = AWARDTYPE_100KMILES
        award['reward'] = reward
        award.save()


# Optimization trick so that we can keep this for consecutive loads
_JSON_PLUGINS_PAYLOAD = None

@route('/plugins.js', name='plugins_js')
class PluginsJSHandler(BaseHandler):

    def get(self):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        global _JSON_PLUGINS_PAYLOAD
        if not _JSON_PLUGINS_PAYLOAD:
            plugins = {}
            for k, urls in self.PLUGINS.items():
                urls = [x.startswith('//') and x or self.static_url(x)
                        for x in urls]
                plugins[k] = urls
            _JSON_PLUGINS_PAYLOAD = tornado.escape.json_encode(plugins)

        self.write('window.PLUGINS=%s;\n' % _JSON_PLUGINS_PAYLOAD)


class AuthenticatedBaseHandler(BaseHandler):

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.write({'error': 'NOTLOGGEDIN'})
            self.finish()


@route('/')
class HomeHandler(BaseHandler):

#    def compute_etag(self):
#        return None

    def render(self, template, **options):
        options['state'] = self.get_state()
        super(HomeHandler, self).render(template, **options)

    def get(self):
        options = {}
        ua = self.request.headers.get('User-Agent')
        if ua and MOBILE_USER_AGENTS.search(ua) and not self.get_cookie('no-mobile'):
            self.redirect('/mobile/')
            return
        self.render('home.html', **options)


@route('/offline/?')
class OfflineHomeHandler(HomeHandler):

    @tornado.web.addslash
    def get(self):
        options = {}
        self.render('offline.html', **options)

@route('/mobile/?')
class MobileHomeHandler(HomeHandler):

    @tornado.web.addslash
    def get(self):
        options = {}
        self.render('mobile.html', **options)

@route('/mobile/exit/')
class ExitMobileHomeHandler(HomeHandler):

    def get(self):
        self.set_cookie('no-mobile', '1')
        self.redirect('/')


@route('/flightpaths/')
class FlightPathsHandler(BaseHandler):

    def check_xsrf_cookie(self):
        pass

    def get(self):
        data = [{u'to': [35.772095999999998, -78.638614500000017],
                 u'from': [37.774929499999999, -122.41941550000001]}]
        self.write(data)

    def post(self):
        print repr(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        print data
        self.write({'status': 'OK'})


@route('/quizzing.json$', name='quizzing')
class QuizzingHandler(AuthenticatedBaseHandler, PictureThumbnailMixin):

    # number between 0 and (inclusive) 1.0 that decides how many coins to
    # give for a percentage.
    PERCENTAGE_COINS_RATIO = 1.0

    #SECONDS = 10
    NO_QUESTIONS = settings.QUIZ_MIN_NO_QUESTIONS
    NO_QUESTIONS_TUTORIAL = settings.QUIZ_NO_QUESTIONS_TUTORIAL

    def points_to_coins(self, points, no_questions=None):
        if not no_questions:
            no_questions = self.NO_QUESTIONS
        max_ = no_questions * Question.HIGHEST_POINTS_VALUE
        percentage = 100 * points / max_
        return int(percentage * self.PERCENTAGE_COINS_RATIO)

    def _teardown(self, user, location):
        for session in (self.db.QuestionSession
                        .find({'user': user['_id'],
                               'location': location['_id'],
                               'finish_date': None})):
            session.delete()

    def render_didyouknow(self, text):
        text = markdown.markdown(
          tornado.escape.linkify(text, extra_params='target="_blank"')
        )
        return text

    def get_intro_html(self, category, location):
        document = self.db.HTMLDocument.find_one({
          'category': category['_id'],
          'location': location['_id']
        })

        if not document and location['city'] == self.NOMANSLAND['city']:
            tutorial = self.db.Category.find_one({'name': u'Tutorial'})
            document = self.db.HTMLDocument()
            document['source'] = TUTORIAL_INTRO
            document['source_format'] = u'markdown'
            document['type'] = u'intro'
            document['location'] = location['_id']
            document['category'] = tutorial['_id']
            document['notes'] = u'this is automatically generated'
            document.save()

        if not document:
            document = self.db.HTMLDocument.find_one({
              'category': category['_id'],
            })

        if document:
            if not document['html']:
                document.update_html()
            return document['html']

    def get(self):
        category = self.get_argument('category')
        category = category.replace('+', ' ')
        category = self.db.Category.find_one({'name': category})
        if not category:
            raise tornado.web.HTTPError(404, 'Invalid category')
        user = self.get_current_user()
        location = self.get_current_location(user)
        data = {}
        data['quiz_name'] = category['name']
        if self.get_argument('start', None):
            self._teardown(user, location)
            session = None
            data['intro'] = self.get_intro_html(category, location)

        else:
            session = (self.db.QuestionSession
                       .find_one({'user': user['_id'],
                                  'category': category['_id'],
                                  'location': location['_id'],
                                  'finish_date': None}))
        if session is None:
            session = self.db.QuestionSession()
            session['user'] = user['_id']
            session['location'] = location['_id']
            session['category'] = category['_id']
            try:
                session['questions'] = self._pick_questions(user, location, category)
            except NoQuestionsError:
                self.write({'error': 'NOQUESTIONS'})
                return
            session.save()

            # check which of these have images that need to be preloaded
            data['pictures'] = []
            for q_id in session['questions']:
                pictures = list(
                    self.db.QuestionPicture
                    .find({'question': q_id})
                )
                if len(pictures) == 4:
                    max_width, max_height = settings.FOUR_PICTURES_WIDTH_HEIGHT
                    kwargs = {'crop': True}
                else:
                    max_width, max_height = settings.PICTURE_QUESTION_WIDTH_HEIGHT
                    kwargs = {}
                for picture in pictures:
                    uri, (width, height) = self.get_thumbnail(
                        picture,
                        (max_width, max_height),
                        **kwargs
                    )
                    url = self.static_url(uri.replace('/static/', ''))
                    data['pictures'].append(url)

        for each in (self.db.SessionAnswer
                     .find({'session': session['_id']})
                     .sort('add_date', -1)  # newest first
                     .limit(1)):
            previous_question = each
            break
        else:
            previous_question = None

        if previous_question:
            if previous_question['answer'] is None:
                # no answer was sent, it must have timed out
                previous_question['timedout'] = True
                previous_question['points'] = 0.0
                previous_question.save()

        question_id = session['questions'].pop(0)
        session.save()
        question = self.db.Question.find_one({'_id': question_id})

        if not question['alternatives_sorted']:
            random.shuffle(question['alternatives'])

        answer = self.db.SessionAnswer()
        answer['question'] = question['_id']
        answer['session'] = session['_id']
        answer.save()

        _no_answers = (self.db.SessionAnswer
                       .find({'session': session['_id']})
                       .count())
        no_questions = self.NO_QUESTIONS
        if category['name'] == u'Tutorial':
            no_questions = self.NO_QUESTIONS_TUTORIAL
        data['no_questions'] = {
          'total': no_questions,
          'number': _no_answers,
          'last': _no_answers == no_questions,
        }

        data['question'] = {
          'text': question['text'],
          'alternatives': question['alternatives'],
          'pictures': []
        }
        pictures = list(question.get_pictures())
        max_width, max_height = (250, 250)
        kwargs = {}
        if len(pictures) == 4:
            max_width, max_height = settings.FOUR_PICTURES_WIDTH_HEIGHT
            kwargs = {'crop': True}
        for picture in pictures:
            uri, (width, height) = self.get_thumbnail(
                picture,
                (max_width, max_height),
                **kwargs
            )
            url = self.static_url(uri.replace('/static/', ''))
            data['question']['pictures'].append({
              'url': url,
              'width': width,
              'height': height,
              'index': picture['index'],
            })
        if len(data['question'].get('pictures', [])) == 4:
            random.shuffle(data['question']['pictures'])
        elif 1 <= len(data['question'].get('pictures', [])) < 4:
            data['question']['picture'] = data['question']['pictures'][0]
            data['question'].pop('pictures')

        data['question']['seconds'] = question['seconds']
        self.write(data)

    def _pick_questions(self, user, location, category, allow_repeats=False):
        filter_ = {
          'location': location['_id'],
          'category': category['_id'],
          'published': True,
        }
        question_ids = []
        no_questions = self.NO_QUESTIONS
        if category['name'] == 'Tutorial':
            no_questions = self.NO_QUESTIONS_TUTORIAL
        while len(question_ids) < no_questions:
            if question_ids:
                this_filter = dict(filter_,
                                   _id={'$nin': question_ids})
            else:
                this_filter = dict(filter_)
            questions = self.db.Question.find(this_filter, ('_id',))
            count = questions.count()
            if not count:
                if allow_repeats:
                    raise NoQuestionsError('Not enough questions')
                else:
                    return self._pick_questions(user, location, category,
                                                allow_repeats=True)

            nth = random.randint(0, count - 1)
            for question in questions.limit(1).skip(nth):
                question_ids.append(question['_id'])

        # no repeats!
        assert len(question_ids) == len(set(question_ids))
        return question_ids

    def _get_next_question(self, session, category, location,
                           allow_repeats=False, previous_question=None):
        filter_ = {
          'location': location['_id'],
          'category': category['_id']
        }
        if previous_question:
            filter_['_id'] = {'$ne': previous_question['_id']}

        if not allow_repeats:
            past_question_ids = set()
            for a in (self.db.SessionAnswer
                       .find({'session': session['_id']})):
                past_question_ids.add(a['question'])
            if past_question_ids:
                if '_id' in filter_:
                    past_question_ids.add(filter_['_id']['$ne'])
                filter_['_id'] = {'$nin': list(past_question_ids)}

        questions = self.db.Question.find(filter_)
        count = questions.count()
        if not count:
            if allow_repeats:
                raise NoQuestionsError("Not enough questions")
            return self._get_next_question(session, category,
                                           location, allow_repeats=True)

        nth = random.randint(0, count - 1)
        for question in questions.limit(1).skip(nth):
            return question

    def post(self):
        user = self.get_current_user()
        location = self.get_current_location(user)

        cache_key = 'questions_answered_stats:%s' % user['_id']
        self.redis.delete(cache_key)

        if self.get_argument('teardown', None):
            # called when the plugin is torn down
            # Use this opportunity to close any unfinished sessions
            self._teardown(user, location)
            self.write({'ok': True})
            return

        filter_ = {
          'user': user['_id'],
          'location': location['_id'],
          'finish_date': None
        }
        if not self.db.QuestionSession.find(filter_).count():
            self.write({'error': 'ALREADYFINISHED'})
            logging.warning("Question session already finished %s" % filter_)
            return

        session, = (self.db.QuestionSession
                    .find(filter_)
                    .sort('add_date', -1)  # newest first
                    .limit(1))

        answer_obj, = (self.db.SessionAnswer
                       .find({'session': session['_id']})
                       .sort('add_date', -1)  # newest first
                       .limit(1))

        data = {}
        if self.get_argument('finish', None):
            session['finish_date'] = datetime.datetime.utcnow()
            session.save()

            if not answer_obj['answer']:
                answer_obj['timedout'] = True
                answer_obj['points'] = 0.0
                answer_obj.save()

            total_points = 0
            rights = []
            summary = []
            for answer in (self.db.SessionAnswer
                           .find({'session': session['_id']})
                           .sort('add_date', 1)  # oldest first
                           ):
                if answer['timedout']:
                    rights.append(False)
                else:
                    rights.append(answer['correct'])
                    total_points += answer['points']
                question = (self.db.Question
                            .find_one({'_id': answer['question']}))
                your_answer = answer['answer']
                correct_answer = question['correct']
                if question.count_pictures() == 4:
                    if your_answer:
                        # re-write your answer as a dict
                        picture = (self.db.QuestionPicture
                                   .find_one({'question': question['_id'],
                                              'index': int(your_answer)}))
                        uri, (width, height) = self.get_thumbnail(
                            picture,
                            (40, 40),
                        )
                        url = self.static_url(uri.replace('/static/', ''))
                        your_answer = {
                          'url': url,
                          'width': width,
                          'height': height,
                        }
                    # re-write correct answer as a dict
                    picture = (self.db.QuestionPicture
                               .find_one({'question': question['_id'],
                                          'index': int(correct_answer)}))
                    uri, (width, height) = self.get_thumbnail(
                        picture,
                        (40, 40),
                    )
                    url = self.static_url(uri.replace('/static/', ''))
                    correct_answer = {
                      'url': url,
                      'width': width,
                      'height': height,
                    }

                summary.append({
                  'question': question['text'],
                  'correct_answer': correct_answer,
                  'your_answer': your_answer,
                  'correct': answer['correct'],
                  'time': (not answer['timedout']
                           and answer['time']
                           or None),
                  'points': answer['points'],
                  'timedout': answer['timedout'],
                  'first_time': answer['first_time'],
                  'first_time_correct': answer['first_time_correct'],
                })
            data['summary'] = summary
            tutorial = self.db.Category.find_one({'name': u'Tutorial'})
            if tutorial['_id'] == session['category']:
                no_questions = (self.db.Question
                                .find({'category': session['category']})
                                .count())
                coins = self.points_to_coins(total_points,
                  no_questions=no_questions)
            else:
                coins = self.points_to_coins(total_points)
            user_settings = self.get_current_user_settings()
            user_settings['coins_total'] += coins
            user_settings.save()

            job = self.db.Job()
            job['user'] = user['_id']
            job['coins'] = coins
            job['category'] = session['category']
            job['location'] = location['_id']
            job.save()

            percentage = 100.0 * sum(rights) / len(rights)

            if percentage >= 100.0 and tutorial['_id'] != session['category']:
                category = self.db.Category.find_one({'_id': session['category']})
                if not self.has_job_award(user, location, category):
                    data_ = {
                      'perfect': percentage == 100.0,
                      'percentage': percentage,
                      'coins': coins,
                    }
                    reward = 100
                    award = self.create_job_award(
                      user,
                      location,
                      category,
                      reward,
                      data_
                    )
                    user_settings['coins_total'] += reward
                    user_settings.save()

                    data['award'] = {
                      'description': award['description'],
                      'id': str(award['_id'])
                    }
            # XXX should make it so that an award is given for completing the
            # tutorial (when you can afford to fly somewhere)
            data['results'] = {
              'total_points': total_points,
              'coins': coins,
              'percentage_right': percentage
            }
        else:
            question = (self.db.Question
                        .find_one({'_id': answer_obj['question']}))

            if question.get('didyouknow'):
                data['didyouknow'] = self.render_didyouknow(question['didyouknow'])
            _count_pictures = question.count_pictures()
            if _count_pictures == 2:
                # include the second picture in the didyouknow text
                max_width, max_height = (200, 200)
                second = list(question.get_pictures())[1]
                uri, (width, height) = self.get_thumbnail(
                    second,
                    (max_width, max_height),
                    **{}
                )
                data['didyouknow_picture'] = {
                    'url': uri,
                    'width': width,
                    'height': height,
                }

            answer = self.get_argument('answer')
            time_ = float(self.get_argument('time'))
            data['correct'] = question.check_answer(answer)
            if not data['correct']:
                data['correct_answer'] = question['correct']
                if question.count_pictures() == 4:
                    # instead of returning the correct answer, return a URL
                    picture = (self.db.QuestionPicture
                               .find_one({'question': question['_id'],
                                          'index': int(question['correct'])}))
                    uri, (width, height) = self.get_thumbnail(
                        picture,
                        (100, 100),
                    )
                    url = self.static_url(uri.replace('/static/', ''))
                    data['correct_answer'] = {
                      'url': url,
                      'width': width,
                      'height': height,
                    }

            time_left = question['seconds'] - time_
            time_bonus_p = round(float(time_left) / question['seconds'], 1)
            data['time_bonus'] = 1 + time_bonus_p
            data['points_value'] = question.get('points_value', 1)
            data['points'] = float(
                data['time_bonus'] *
                data['points_value'] *
                data['correct']
            )
            # if you got it right and have never got it right before, then
            # double the points
            if self._first_time(user, question, session):
                answer_obj['first_time'] = True

            if data['correct']:
                if self._first_time_correct(user, question, session):
                    data['points'] *= 2
                    answer_obj['first_time_correct'] = True
                    data['first_time_correct'] = True
            data['points'] = round(data['points'], 1)
            assert isinstance(data['points_value'], int)

            data['enable_rating'] = True
            tutorial = self.db.Category.find_one({'name': 'Tutorial'})
            if tutorial['_id'] == question['category']:
                data['enable_rating'] = False

            answer_obj['time'] = time_
            answer_obj['answer'] = answer
            answer_obj['correct'] = data['correct']
            answer_obj['points'] = data['points']
            answer_obj['timedout'] = False
            answer_obj.save()

            if question['author']:
                earning = self.db.QuestionAnswerEarning()
                earning['question'] = question['_id']
                earning['answer'] = answer_obj['_id']
                earning['user'] = question['author']
                earning['coins'] = QuestionWriterHandler.COINS_EARNING_VALUE
                earning.save()

                # also, add it to the users balance immediately
                author_settings = (self.db.UserSettings
                                   .find_one({'user': question['author']}))
                author_settings['coins_total'] += earning['coins']
                author_settings.save()

        self.write(data)

    def _first_time(self, user, question, session):
        for s in (self.db.QuestionSession.collection
                  .find({'user': user['_id'],
                         'location': session['location'],
                         'category': session['category'],
                         'finish_date': {'$ne': None}},
                         ('_id',))):
            if (self.db.SessionAnswer
                .find({'session': s['_id'],
                       'question': question['_id']})
                .count()):
                return False
        return True

    def _first_time_correct(self, user, question, session):
        for s in (self.db.QuestionSession.collection
                  .find({'user': user['_id'],
                         'location': session['location'],
                         'category': session['category'],
                         'finish_date': {'$ne': None}},
                         ('_id',))):
            if (self.db.SessionAnswer
                .find({'session': s['_id'],
                       'question': question['_id'],
                       'first_time_correct': True,})
                .count()):
                return False
        return True

@route('/questionrating.json$', name='question_rating')
class QuestionRatingHandler(AuthenticatedBaseHandler):

    def post(self):
        score = int(self.get_argument('score'))
        assert score >= 1 and score <= 5, score
        user = self.get_current_user()
        location = self.get_current_location(user)
        for session in (self.db.QuestionSession
                        .find({'user': user['_id'],
                               'location': location['_id']},
                              ('_id',))
                        .sort('add_date', -1)
                        .limit(1)):
            for each in (self.db.SessionAnswer
                         .find({'session': session['_id'],
                                'correct': {'$ne': None}},
                               ('question', 'correct', 'add_date'))
                         .sort('add_date', -1)
                         .limit(1)):
                # before we add, check that it wasn't already recorded
                time_ago = each['add_date'] - datetime.timedelta(seconds=10)
                filter_ = {'question': each['question'],
                           'user': user['_id'],
                           'add_date': {'$gte': time_ago}}
                if self.db.QuestionRating.find(filter_).count():
                    continue
                rating = self.db.QuestionRating()
                rating['question'] = each['question']
                rating['user'] = user['_id']
                rating['score'] = score
                rating['correct'] = each['correct']
                rating.save()

                for each in (self.db.QuestionRatingTotal
                             .find({'question': each['question']})):
                    each.delete()

                self.write({'ok': 'Thanks'})
                return

        self.write({'error': 'CANTRATEQUESTION'})


@route('/settings.json$', name='settings')
class SettingsHandler(AuthenticatedBaseHandler):

    def get(self):
        user = self.get_current_user()

        if self.get_argument('check-username', None):
            username = self.get_argument('check-username').strip()
            wrong = self._check_username(username, user)
            self.write({'wrong': wrong})
            return

        user_settings = self.get_user_settings(user)
        assert user_settings
        data = {}
        data['disable_sound'] = user_settings['disable_sound']
        data['unsubscribe_emails'] = user_settings['unsubscribe_emails']
        data['username'] = user['username']
        data['anonymous'] = user['anonymous']
        data['first_name'] = user['first_name']
        data['last_name'] = user['last_name']
        self.write(data)

    def _check_username(self, username, user):
        if re.findall('[^\w\.-_]', username):
            return "Can't contain spaces"
        if len(username) > 50:
            return "Too long"
        search = {'username': re.compile(re.escape(username), re.I),
                  '_id': {'$ne': user['_id']}}
        if self.db.User.find_one(search):
            return "Taken"

    def post(self):
        user = self.get_current_user()
        username = self.get_argument('username', None)
        if username:
            user['username'] = username
            if not user['anonymous']:
                user['first_name'] = self.get_argument('first_name',
                                                       user['first_name']).strip()
                user['last_name'] = self.get_argument('last_name',
                                                      user['last_name']).strip()
            user.save()

        user_settings = self.get_user_settings(user)
        disable_sound = bool(self.get_argument('disable_sound', False))
        unsubscribe_emails = bool(self.get_argument('unsubscribe_emails', False))
        user_settings['disable_sound'] = disable_sound
        user_settings['unsubscribe_emails'] = unsubscribe_emails
        user_settings.save()
        self.get()


@route('/miles.json$', name='miles')
class MilesHandler(AuthenticatedBaseHandler):

    def get(self):
        user = self.get_current_user()
        data = {}
        _cities = set()
        for each in self.db.Flight.find({'user': user['_id']}):
            _cities.add(each['from'])
            _cities.add(each['to'])
        data['no_cities'] = max(1, len(_cities))
        # add +1 for the moon :)
        data['no_cities_possible'] = (self.db.Location
                                      .find({'available': True})
                                      .count()) + 1
        data['flights'] = self.get_flights(user)
        data['percentage'] = 0
        self.write(data)

    def get_flights(self, user):
        flights = []
        filter_ = {'user': user['_id']}
        _locations = {}
        for each in (self.db.Flight
                     .find(filter_)
                     .sort('add_date', 1)):  # oldest first

            if each['from'] not in _locations:
                _locations[each['from']] = (self.db.Location
                                            .find_one({'_id': each['from']})
                                            .dictify())
            if each['to'] not in _locations:
                _locations[each['to']] = (self.db.Location
                                          .find_one({'_id': each['to']})
                                          .dictify())
            flight = {
              'from': _locations[each['from']],
              'to': _locations[each['to']],
              'miles': int(each['miles']),
              'date': each['add_date'].strftime(FULL_DATE_FMT),
            }
            flights.append(flight)
        return flights


class BankingMixin(object):

    def calculate_compound_interest(self, deposits):
        total = 0
        today = datetime.datetime.utcnow()
        for deposit in deposits:
            days = (today - deposit['add_date']).days
            if not days:
                continue
            rate = deposit['interest_rate'] / 100.0 + 1.0
            total += deposit['amount'] * rate ** days - deposit['amount']
        return total


@route('/coins.json$', name='coins')
class CoinsHandler(AuthenticatedBaseHandler, BankingMixin):

    def get(self):
        user = self.get_current_user()
        data = {}
        if self.get_argument('transactions-page', None) is not None:
            data['transactions'], count = self.get_transactions(user)
            data['count_transactions'] = count
        if self.get_argument('jobs-page', None) is not None:
            data['jobs'], count = self.get_jobs(user)
            data['count_jobs'] = count
        if self.get_argument('earnings-page', None) is not None:
            data['earnings'], total = self.get_earnings(user)
            data['earnings_total'] = total
        if self.get_argument('banks-page', None) is not None:
            data['banks'], total = self.get_banks(user)
            data['banks_total'] = total
        self.write(data)

    def get_jobs(self, user, limit=10):
        jobs = []
        filter_ = {'user': user['_id']}
        records = self.db.Job.collection.find(filter_)
        count = records.count()
        skip = limit * int(self.get_argument('jobs-page', 0))

        # optimization
        _locations = {}
        _categories = {}

        for each in (records
                     .limit(limit)
                     .skip(skip)
                     .sort('add_date', -1)):  # newest first
            if each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})
            location = _locations[each['location']]
            assert location

            if each['category'] not in _categories:
                _categories[each['category']] = \
                  self.db.Category.find_one({'_id': each['category']})
            category = _categories[each['category']]
            assert category
            job = {
              'description': category['name'],
              'coins': each['coins'],
              'location': unicode(location),
              'date': each['add_date'].strftime(FULL_DATE_FMT),
            }
            jobs.append(job)
        return jobs, count

    def get_transactions(self, user, limit=10):
        transactions = []
        filter_ = {'user': user['_id']}
        records = self.db.Transaction.collection.find(filter_)
        count = records.count()
        skip = limit * int(self.get_argument('transactions-page', 0))
        for each in (records
                     .limit(limit)
                     .skip(skip)
                     .sort('add_date', -1)):  # newest first
            transaction = {
              'cost': each['cost'],
              'date': each['add_date'].strftime(FULL_DATE_FMT),
            }
            if each['flight']:
                flight = self.db.Flight.find_one({'_id': each['flight']})
                from_ = self.db.Location.find_one({'_id': flight['from']})
                to = self.db.Location.find_one({'_id': flight['to']})
                description = ('Flying from %s to %s (%s miles)' %
                               (from_, to, commafy(int(flight['miles']))))
                type_ = 'flight'
            else:
                raise NotImplementedError
            transaction['description'] = description
            transaction['type'] = type_
            transactions.append(transaction)
        return transactions, count

    def get_earnings(self, user, limit=20):
        earnings = []
        total = 0
        filter_ = {'user': user['_id']}
        records_questions = self.db.QuestionAnswerEarning.collection.find(filter_)
        records_interests = self.db.InterestEarning.collection.find(filter_)

        earnings_by_question = defaultdict(int)
        _questions = {}
        for question in (self.db.Question.collection
                         .find({'author': user['_id']},
                               ('text', 'correct'))):
            _questions[question['_id']] = question
        for each in records_questions:
            question = _questions[each['question']]
            earning = {
              'type': 'question',
              'coins': each['coins'],
              'date': each['add_date'].strftime(FULL_DATE_FMT),
              'description': question['text'],
            }
            group_key = '%s%s' % (question['_id'], each['add_date'].strftime('%m%Y'))
            if group_key not in earnings_by_question:
                earnings_by_question[group_key] = {
                  'type': 'Written question',
                  'description': ('<em>"%s"</em> (%s)' %
                                  (question['text'], question['correct'])),
                  'coins': each['coins'],
                  'date_description': each['add_date'].strftime('%B, %Y'),
                  'date': each['add_date'],
                }
            else:
                earnings_by_question[group_key]['coins'] += each['coins']
            total += each['coins']
        for each in records_interests.sort('add_date', -1):
            bank = (self.db.Bank.collection
                    .find_one({'_id': each['bank']}, ('name', 'location')))
            location = (self.db.Location
                        .find_one({'_id': bank['location']}))
            earning = {
              'type': 'Bank interest',
              'coins': each['coins'],
              'date_description': each['add_date'].strftime(FULL_DATE_FMT),
              'date': each['add_date'],
              'description': '%s in %s' % (bank['name'], location)
            }
            earnings.append(earning)
            total += each['coins']

        earnings.extend(earnings_by_question.values())

        earnings.sort(key=lambda x: x['date'], reverse=True)
        earnings = earnings[:limit]
        for each in earnings:
            each['date'] = each.pop('date_description')

        return earnings, total

    def get_banks(self, user):
        banks = {}

        current_location = self.get_current_location(user)

        filter_ = {'user': user['_id']}
        bank_ids = (self.db.Deposit.collection
                    .find(filter_)
                    .distinct('bank'))
        banks = []
        total_total = 0
        for bank_id in bank_ids:
            bank = self.db.Bank.collection.find_one({'_id': bank_id})
            cities = []
            in_current_location = False
            for each in (self.db.Bank.collection
                         .find({'name': bank['name']}, ('location',))):
                location = self.db.Location.find_one({'_id': each['location']})
                if location == current_location:
                    in_current_location = True
                else:
                    cities.append(unicode(location))

            deposits = (self.db.Deposit.collection
                        .find(dict(filter_, bank=bank_id)))
            deposited = sum(x['amount'] for x in deposits)
            deposits.rewind()
            interest = self.calculate_compound_interest(deposits)
            total = deposited + interest
            banks.append({
              'name': bank['name'],
              'deposited': int(deposited),
              'total': int(total),
              'interest': int(round(interest)),
              'locations': cities,
              'in_current_location': in_current_location,
            })
            total_total += total

        return banks, int(total_total)


@route('/location.json$', name='location')
class LocationHandler(AuthenticatedBaseHandler):

    def get(self):
        ip_location = None
        ip = self.get_current_ip()
        if ip:
            cache_key = 'iplookup-%s' % ip
            value = self.redis.get(cache_key)
            if value:
                ip_location = tornado.escape.json_decode(value)
                print ip_location

        locations = []
        for location in (self.db.Location
                         .find({'available': True})
                         .sort('city', 1)):
            if not self.enough_questions(location):
                continue

            option = {
              'name': unicode(location),
              'id': str(location['_id'])
            }
            if ip_location:
                d = geopy_distance(
                  (ip_location['lat'], ip_location['lng']),
                  (location['lat'], location['lng'])
                )
                option['distance'] = int(d.miles)
            locations.append(option)
        if ip_location:
            locations.sort(lambda x, y: cmp(x['distance'], y['distance']))
        self.write({'locations': locations})

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
        self.write({'state': data})


class FlightFinderMixin(object):

    BASE_PRICE = 100  # coins

    def get_destinations(self, user, user_settings, current_location,
                         only_affordable=False,
                         ticket_progress=False,
                         ticket_progress_min=None):
        destinations = []
        for location in (self.db.Location
                          .find({'_id': {'$ne': current_location['_id']},
                                 'available': True})):
            if not self.enough_questions(location):
                continue
            distance = calculate_distance(current_location, location)
            cost = self.calculate_cost(distance.miles, user)
            if only_affordable:
                if cost > user_settings['coins_total']:
                    continue

            destination = {
              'id': str(location['_id']),
              'code': location['code'],
              'name': unicode(location),
              'city': location['city'],
              'locality': location['locality'],
              'country': location['country'],
              'cost': cost,
              'canafford': cost <= user_settings['coins_total'],
              'miles': distance.miles,
              'lat': location['lat'],
              'lng': location['lng'],
            }
            if ticket_progress:
                destination['ticket_info'] = 'bla coins'
                percentage = 100.0 * user_settings['coins_total'] / cost
                if percentage < ticket_progress_min:
                    continue
                destination['percentage'] = min(100, int(percentage))

            destinations.append(destination)

        if not only_affordable and not ticket_progress:
            destinations.append({
              'id': 'moon',
              'code': '',
              'city': '',
              'country': '',
              'locality': 'space',
              'name': 'Moon',
              'cost': 1000000,
              'miles': 238857,
              'canafford': False
            })

        if ticket_progress:
            def sorter(x, y):
                c = cmp(x['percentage'], y['percentage'])
                if not c:
                    # cheapest first
                    c = cmp(y['cost'], x['cost'])
                return c
            destinations.sort(sorter,
                              reverse=True)

        return destinations

    def calculate_cost(self, miles, user):
        return self.BASE_PRICE + int(round(miles * .08))


class LeagueMixin(object):

    def get_pending_invites(self, this_user):
        invites = []
        # it could either be from invites
        for each in self.get_pending_friendship_invites():
            user = self.db.User.find_one({'_id': each['user']})
            invites.append({
              'user': self.get_name(user),
              'total_earned': self.get_total_earned(user)['coins'],
              'id': str(user['_id'])
            })

        for each in self.db.Friendship.find({'to': this_user['_id'], 'mutual': False}):
            user = self.db.User.find_one({'_id': each['user']})
            invites.append({
              'user': self.get_name(user),
              'total_earned': self.get_total_earned(user)['coins'],
              'id': str(user['_id'])
            })

        return invites

    def get_highscore_fast(self, user):
        # return a list of just user ids all sorted by total earning
        users = []
        users.append((
            self.get_total_earned(user, only_coins=True),
            user['_id']
        ))
        for friendship in (self.db.Friendship.collection
                           .find({'user': user['_id']}, ('to',))):
            users.append((
                self.get_total_earned(friendship['to'], only_coins=True),
                friendship['to'],
            ))
        users.sort(reverse=True)
        return users


class FlagMixin(object):

    FLAGS_CONTAINER = {
        64: 'images/flags/64',
        16: 'images/flags/16',
    }
    # if not in this list, it'll do a good job guessing
    FLAGS = {
        #'Sweden': 'Sweden.png',
    }

    def get_flag(self, location, size):
        root = self.FLAGS_CONTAINER[size]
        country = location['country']
        if not country and location['name'] == 'Moon':
            country = 'Moon'
        guess = os.path.join(root, country.replace(' ', '-') + '.png')
        full = os.path.join(self.application.settings['static_path'], guess)
        if os.path.isfile(full):
            return self.static_url(guess)
        if country not in self.FLAGS:
            logging.warn("No flag for %r" % country)
            return
        return self.static_url(os.path.join(self.FLAGS_CONTAINER,
                                            self.FLAGS[country]))


@route('/city.json$', name='city')
class CityHandler(AuthenticatedBaseHandler,
                  PictureThumbnailMixin,
                  FlightFinderMixin,
                  BankingMixin,
                  LeagueMixin,
                  FlagMixin):

    def get_ambassadors_html(self, location):
        filter_ = {
          'type': 'ambassadors',
          'country': location['country'],
        }
        document = self.db.HTMLDocument.find_one(filter_)
        if document:
            if not document['html']:
                document.update_html()
            return document['html']

    def get_intro_html(self, location):
        filter_ = {
          'type': 'intro',
          'location': location['_id'],
        }
        document = self.db.HTMLDocument.find_one(filter_)
        if document:
            if not document['html']:
                document.update_html()
            return document['html']

    def get(self):
        data = {}
        user = self.get_current_user()
        location = self.get_current_location(user)

        get = self.get_argument('get', None)
        if get == 'ambassadors':
            data['ambassadors'] = self.get_ambassadors_html(location)
        elif get == 'jobs':
            data['jobs'] = self.get_available_jobs(user, location)
            data['day_number'] = self.get_day_number(user, location)
        elif get == 'intro':
            data['intro'] = self.get_intro_html(location)
        elif get == 'pictures':
            data['pictures'] = self.get_pictures(location)
        elif get == 'messages':
            data['messages'] = self.get_messages(location, limit=10)
        elif get:
            raise tornado.web.HTTPError(404, 'Invalid get')
        else:
            data['name'] = unicode(location)
            data['city'] = location['city']
            data['locality'] = location['locality']
            data['country'] = location['country']
            data['lat'] = location['lat']
            data['lng'] = location['lng']
            data['about_jobs'] = self.get_about_jobs(location, user)
            data['about_flights'] = self.get_about_flights(location, user)
            data['about_writings'] = self.get_about_writings(location, user)
            data['about_question_writing'] = self.get_about_question_writing(location, user)
            data['about_pictures'] = self.get_about_pictures(location)
            data['about_banks'] = self.get_about_banks(location, user)
            data['about_league'] = self.get_about_league(user)
            #data['count_pictures'] = self.get_pictures_count(location)
            #data['count_messages'] = self.get_messages_count(location)
            #data['count_banks'] = self.get_banks_count(location)
            #data['has_introduction'] = bool(self.get_intro_html(location))
            #data['has_ambassadors'] = bool(self.get_ambassadors_html(location))
            flag = self.get_flag(location, 64)
            if flag:
                data['flag'] = flag
            data['state'] = self.get_state()

            data['newsitem'] = self.get_unread_newsitem(user)
            data['count_newsitems'] = self.get_count_newsitems(user)

        self.write(data)

    def get_unread_newsitem(self, user):
        for each in (self.db.NewsItem.collection
                     .find({'user': user['_id'],
                            'read': False})
                     .sort('add_date', 1)
                     .limit(1)):
            return {
                'id': str(each['_id']),
                'title': each['title'],
            }

    def get_count_newsitems(self, user):
        return self.db.NewsItem.find({'user': user['_id']}).count()

    def get_day_number(self, user, location):
        day = 1
        for job in (self.db.Job
                    .find({'user': user['_id']},
                          ('location', 'add_date', '_id'))
                    .sort('add_date', -1)):
            if job['location'] != location['_id']:
                break
            day += 1
        return day

    def get_about_jobs(self, location, user):
        earning_total = 0
        unique_categories = []
        _categories = {}
        _jobs = (self.db.Job.collection
                 .find({'user': user['_id'], 'location': location['_id']}))
        for job in _jobs:
            earning_total += job['coins']
            if job['category'] not in _categories:
                _categories[job['category']] = (self.db.Category.collection
                                           .find_one({'_id': job['category']}))
            _category = _categories[job['category']]
            if _category['name'] not in unique_categories:
                unique_categories.append(_category['name'])

        text = ""
        if earning_total:
            text = ("You have earned <strong>%s coins</strong> working as "
                    % earning_total)
            if len(unique_categories) > 2:
                text += ', '.join(unique_categories[:-1])
                text += ' and %s' % unique_categories[-1]
            else:
                text += ' and '.join(unique_categories)
            text += '.'
        else:
            info = self.get_available_jobs(user, location)
            categories = [x['description'] for x in info]
            text = "You can work as "
            if len(categories) > 2:
                text += ', '.join(categories[:-1])
                text += ' and %s' % categories[-1]
            else:
                text += ' and '.join(categories)
            text += '.'

        return text

    def get_about_flights(self, location, user):
        destinations = self.get_destinations(
            user,
            self.get_user_settings(user),
            location,
        )
        cheapest = sorted(destinations, key=lambda x: x['cost'])[0]
        text = ("The cheapest ticket right now is going to "
                "<strong>%s</strong> for %s coins "
                % (cheapest['name'], cheapest['cost']))

        if cheapest['canafford']:
            text += "which you <strong>can afford</strong> right now."
        else:
            text += "which you can <strong>not afford</strong> yet."

        return text.strip()

    def get_about_writings(self, location, user):
        your_messages = (self.db.LocationMessage.collection
                         .find({'user': user['_id'],
                                'location': location['_id']}))
        all_messages = (self.db.LocationMessage.collection
                        .find({'user': {'$ne': user['_id']},
                               'location': location['_id'],
                               'censored': False}))
        your_messages_count = your_messages.count()
        all_messages_count = all_messages.count()
        if your_messages_count:
            text = "You have written "
            if your_messages_count == 1:
                text += "<strong>one message</strong>"
            else:
                text += "<strong>%s messages</strong>" % your_messages_count
            text += " on the wall in this city."
        elif all_messages_count:
            text = "Travellers have left "
            if all_messages_count == 1:
                text += "<strong>one message</strong>"
            else:
                text += "<strong>%s messages</strong>" % all_messages_count
            text += " on the wall in this city. "
        else:
            text = "Be the first to write a message on the wall in this city."
        return text.strip()

    def get_about_question_writing(self, location, user):
        count_written = (self.db.Question
                         .find({'author': user['_id'],
                               'location': location['_id']})
                         .count())
        if count_written:
            count_published = (self.db.Question
                               .find({'author': user['_id'],
                                      'location': location['_id'],
                                      'published': True})
                               .count())
            if count_published:
                text = "You have "
                if count_published == 1:
                    text += "<strong>1 question</strong>"
                else:
                    text += "<strong>%s questions</strong>" % count_published
                text += " questions published! "
                total = 0
                for q in (self.db.Question
                          .find({'author': user['_id'],
                                 'location': location['_id'],
                                 'published': True},
                                ('_id',))):
                    for each in (self.db.QuestionAnswerEarning.collection
                                 .find({'question': q['_id']}, ('coins',))):
                        total += each['coins']
                text += ("Your questions have earned you "
                         "<strong>%s coins</strong>!"
                         % (total, )
                         )
            else:
                text = "You have written "
                if count_written == 1:
                    text += "<strong>1 question</strong>"
                else:
                    text += "<strong>%s questions</strong>" % count_written
                text += " questions. But not of them are published yet."
        else:
            text = ("Writing your own questions is a great way of earning "
                    "lots of coins. You earn coins every time someone plays "
                    "your published questions.")
        return text.strip()

    def get_about_pictures(self, location):
        count_pictures = (self.db.LocationPicture
                          .find({'location': location['_id'],
                                 'published': True})
                          .count())
        if count_pictures:
            if count_pictures == 1:
                text = "There is currently only "
                text += "<strong>1 picture</strong>"
            else:
                text = "There are currently "
                text += "<strong>%s pictures</strong>" % count_pictures
            text += " uploaded."
        else:
            text = "Unfortunately, there are no pictures available yet."
        return text.strip()

    def get_about_banks(self, location, user):
        banks = self.db.Bank.collection.find({'location': location['_id'],
                                              'open': True})
        count_banks = banks.count()
        if count_banks:
            if count_banks == 1:
                text = "There is currently "
                text += "<strong>1 bank</strong>"
            else:
                text = "There are currently "
                text += "<strong>%s banks</strong>" % count_banks
            text += " open in this city. "

            bank_ids = [x['_id'] for x in banks]
            deposits = (self.db.Deposit.collection
                        .find({'bank': {'$in': bank_ids},
                               'user': user['_id']}))
            sum_ = sum(x['amount'] for x in deposits)
            if sum_:
                deposits.rewind()
                interest = self.calculate_compound_interest(deposits)
                interest = int(round(interest))
                text += "You have deposited a total of "
                text += "<strong>%s coins</strong> " % sum_
                text += "with a potential of "
                text += "<strong>%s coins</strong> interest!" % interest
            else:
                text += "You currently have no coins deposited."
        else:
            text = ("There are currently <strong>no open banks</strong> "
                    "in this city.")
        return text

    def get_about_league(self, user):
        text = ""
        invites = self.get_pending_invites(user)
        if invites:
            if len(invites) == 1:
                text = ("You have a pending invite from "
                        "<strong>%s</strong>." % invites[0]['user']
                        )
            else:
                text += "You have %s pending invites." % len(invites)
            text += "<br>"
        users_rankings = {}
        for i, (total, user_id) in enumerate(self.get_highscore_fast(user)):
            users_rankings[user_id] = (i + 1, total)
        text = ("You are current number <strong>%s</strong> "
                "(of %s) "
                "in your League of Friends."
                % (
                   users_rankings[user['_id']][0],
                   len(users_rankings)
                   )
                )

        return text

    def get_banks_count(self, location):
        search = {'location': location['_id']}
        return self.db.Bank.find(search).count()

    def get_pictures_count(self, location):
        search = {'location': location['_id'], 'published': True}
        return self.db.LocationPicture.find(search).count()

    def get_pictures(self, location):
        pictures = []
        search = {'location': location['_id'], 'published': True}
        for item in (self.db.LocationPicture
                     .find(search)
                     .sort('index')):
            uri, (width, height) = self.get_thumbnail(item, (700, 700))  # XXX might need some more thought
            picture = {
              'src': uri,
              'width': width,
              'height': height,
              'title': item['title'],
            }
            if item['description']:
                picture['description'] = item['description']  # XXX should this be markdown?
            if item['copyright']:
                picture['copyright'] = item['copyright']
            if item['copyright_url']:
                picture['copyright_url'] = item['copyright_url']
            pictures.append(picture)
        return pictures

    def get_messages(self, location, limit=5):
        search = {'location': location['_id']}
        messages = []
        _users = {}
        _users_settings = {}
        _locations = {}
        for item in (self.db.LocationMessage
                     .find(search)
                     .limit(limit)
                     .sort('add_date', -1)):
            if item['user'] not in _users:
                _users[item['user']] = (self.db.User
                                        .find_one({'_id': item['user']}))
            if item['user'] not in _users_settings:
                _users_settings[item['user']] = (self.db.UserSettings
                                            .find_one({'user': item['user']}))
            user = _users[item['user']]
            user_settings = _users_settings[item['user']]

            if user['current_location'] not in _locations:
                _locations[user['current_location']] = (self.db.Location
                                 .find_one({'_id': user['current_location']}))
            current_location = _locations[user['current_location']]

            messages.append({
              'message': item['message'],
              'username': user['first_name'] or user['username'],
              'miles': user_settings['miles_total'],
              'current_location': unicode(current_location),
              'time_ago': smartertimesince(item['add_date'],
                                           datetime.datetime.utcnow()),
            })
        return messages

    def get_messages_count(self, location):
        return (self.db.LocationMessage
                .find({'location': location['_id']})
                .count())

    def get_available_jobs(self, user, location):
        categories = defaultdict(int)
        point_values = defaultdict(int)
        _categories = dict((x['_id'], x)
                           for x in self.db.Category.find())

        nomansland = (self.db.Location
                      .find_one({'city': self.NOMANSLAND['city']}))
        if nomansland:
            if not (self.db.Question
                    .find({'location': nomansland['_id']})
                    .count()):
                # we need to create the tutorial questions
                self.create_tutorial_questions(nomansland)

        for q in (self.db.Question
                  .find({'location': location['_id'],
                         'published': True})):
            category = _categories[q['category']]
            categories[category['name']] += 1
            point_values[category['name']] += q['points_value']

        jobs = []
        for _id, category in sorted(_categories.items(),
                                    lambda x, y: cmp(x[1]['name'], y[1]['name'])):
            no_questions = categories[category['name']]
            if location == nomansland:
                # you're in Nomansland
                if category['name'] != 'Tutorial':
                    continue
            elif no_questions < QuizzingHandler.NO_QUESTIONS:
                continue

            experience = None
            _earned = 0
            for job in (self.db.Job
                        .find({'user': user['_id'],
                               'category': _id,
                               'location': location['_id']},
                              ('coins',))):
                _earned += job['coins']
            if _earned:
                experience = "you have earned %s coins" % _earned
            else:
                experience = "you have not yet completed this"

            job = {
              'type': 'quizzing',
              'category': category['name'],
              'description': category['name'],
              'experience': experience,
            }
            jobs.append(job)

        _center_search = {'country': location['country'],
                          'locality': location['locality']}
        _center = self.db.PinpointCenter.find_one(_center_search)
        if not _center and not location['locality']:
            _center_search = {'country': location['country']}
            _center = self.db.PinpointCenter.find_one(_center_search)

        if _center:
            _earned = 0
            category = self.db.Category.find_one({'name': PinpointHandler.CATEGORY_NAME})
            for job in self.db.Job.find({'user': user['_id'],
                                         'location': location['_id'],
                                         'category': category['_id']},
                                         ('coins',)):
                _earned += job['coins']

            if _earned:
                experience = "you have earned %s coins" % _earned
            else:
                experience = "you have not yet completed this"
            _cities = self.db.Location.find(_center_search)
            if _cities.count() > PinpointHandler.NO_QUESTIONS:
                description = 'Geographer'
                jobs.append({
                  'type': 'pinpoint',
                  'description': description,
                  'experience': experience,
                })

        picture_detective_job = self._get_picture_detective_jobs(user, location)
        if picture_detective_job:
            jobs.append(picture_detective_job)
        jobs.sort(lambda x, y: cmp(x['description'], y['description']))
        return jobs

    def create_tutorial_questions(self, location):
        tutorial = self.db.Category.find_one({'name': u'Tutorial'})
        if not tutorial:
            tutorial = self.db.Category()
            tutorial['name'] = u'Tutorial'
            tutorial.save()

        q = self.db.Question()
        q['text'] = u'Which continent is China in?'
        q['correct'] = u'Asia'
        q['alternatives'] = [u'Asia', u'Europe', u'Africa', u'South America']
        q['points_value'] = 5
        q['seconds'] = 20
        q['location'] = location['_id']
        q['category'] = tutorial['_id']
        q['published'] = True
        q.save()

        q = self.db.Question()
        q['text'] = u'Which of these can travel the FASTEST?'
        q['correct'] = u'Airplane'
        q['alternatives'] = [u'Airplane', u'Train', u'Car', u'Boat']
        q['points_value'] = 5
        q['seconds'] = 20
        q['location'] = location['_id']
        q['category'] = tutorial['_id']
        q['published'] = True
        q.save()

        q = self.db.Question()
        q['text'] = u'What are cigars made of?'
        q['correct'] = u'Tobacco'
        q['alternatives'] = [u'Tobacco', u'Paper', u'Bark', u'Dirt']
        q['points_value'] = 5
        q['seconds'] = 20
        q['location'] = location['_id']
        q['category'] = tutorial['_id']
        q['published'] = True
        q.save()

    def _get_picture_detective_jobs(self, user, location):
        # Picture detective job

        category, = (self.db.Category
                     .find({'name': PictureDetectiveHandler.CATEGORY_NAME}))
        questions = self.db.Question.find({'location': location['_id'],
                                           'published': True,
                                           'category': category['_id']},
                                           ('_id',))
        left = questions.count()
        sessions = (self.db.QuestionSession
                    .find({'user': user['_id'],
                           'category': category['_id'],
                           'location': location['_id']},
                           ('_id',)))

        #for session in sessions:
        session_ids = [x['_id'] for x in sessions]
        answered_questions = (self.db.SessionAnswer
                   .find({'session': {'$in': session_ids}},
                          ('question',)))
        answered_questions = [x['question'] for x in answered_questions]
        left = 0
        for question in questions:
            if question['_id'] in answered_questions:
                continue
            left += 1
        # XXX consider doing a count instead.
        if left:
            return {'type': 'picturedetective',
                    'description': 'Picture Detective (%d left)' % left,
                    }

    def post(self):
        # Currently used for posting messages.
        message = self.get_argument('message').strip()
        user = self.get_current_user()
        location = self.get_current_location(user)
        location_message = self.db.LocationMessage()
        location_message['message'] = message
        location_message['user'] = user['_id']
        location_message['location'] = location['_id']
        location_message.save()
        messages = self.get_messages(location, limit=1)
        self.write({'messages': messages})


@route('/picturedetective.json$', name='picturedetective')
class PictureDetectiveHandler(QuizzingHandler):

    CATEGORY_NAME = u'Picture Detective'

    # number between 0 and (inclusive) 1.0 that decides how many coins to
    # give for a percentage.
    PERCENTAGE_COINS_RATIO = 1.0

    def get(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        category = self.db.Category.find_one({'name': self.CATEGORY_NAME})

        # temporary solution
        if 0:
            print "TEMPORARY HACK IN PLACE"
            for x in self.db.QuestionSession.find({'category': category['_id'],
                                                   'user': user['_id'],
                                                   'location': current_location['_id'],
                                                   #'finish_date': None
                                                   }):
                for y in self.db.SessionAnswer.find({'session': x['_id']}):
                    y.delete()
                x.delete()

        session = self.db.QuestionSession()
        session['user'] = user['_id']
        session['category'] = category['_id']
        session['location'] = current_location['_id']
        session.save()

        try:
            question = self._get_next_question(user, session, category, current_location)
        except NoQuestionsError:
            self.write({'error': 'NOQUESTIONS'})
            return

        answer_obj = self.db.SessionAnswer()
        answer_obj['session'] = session['_id']
        answer_obj['question'] = question['_id']
        answer_obj.save()

        pictures = []
        for item in (self.db.QuestionPicture
                     .find({'question': question['_id']})
                     .sort('index')):
            uri, (width, height) = self.get_thumbnail(item, (300, 300))
            url = self.static_url(uri.replace('/static/', ''))
            picture = {
              'src': url,
              'width': width,
              'height': height,
            }
            pictures.append(picture)

        self.write({
            'question': question['text'],
            'seconds': len(pictures),
            'pictures': pictures,
        })

    def _get_next_question(self, user, session, category, location):
        question_filter = {
          'location': location['_id'],
          'category': category['_id'],
        }

        past_question_ids = set()
        session_filter = {
          'user': user['_id'],
          'location': location['_id'],
          'category': category['_id'],
          'finish_date': {'$ne': None},
        }

        for other_session in self.db.QuestionSession.find(session_filter):
            for answer in (self.db.SessionAnswer
                           .find({'session': other_session['_id']})):
                past_question_ids.add(answer['question'])

        if past_question_ids:
            question_filter['_id'] = {'$nin': list(past_question_ids)}

        questions = self.db.Question.find(question_filter)
        count = questions.count()
        if not count:
            raise NoQuestionsError("No more questions")

        nth = random.randint(0, count - 1)
        for question in questions.limit(1).skip(nth):
            return question

    def post(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        category = self.db.Category.find_one({'name': self.CATEGORY_NAME})
        session, = (self.db.QuestionSession
                     .find({'user': user['_id'],
                            'category': category['_id'],
                            'location': current_location['_id'],
                            'finish_date': None})
                     .sort('start_date', 1)
                     .limit(1))
        answer_obj, = (self.db.SessionAnswer
                       .find({'session': session['_id']}))
        question = self.db.Question.find_one({'_id': answer_obj['question']})

        answer = self.get_argument('answer', None)
        timedout = self.get_argument('timedout', False)
        if timedout == 'false':
            timedout = False
        seconds_left = int(self.get_argument('seconds_left', 0))
        seconds_total = (self.db.QuestionPicture
                         .find({'question': question['_id']})
                         .count())

        data = {}
        data['points'] = 0
        data['coins'] = 0
        answer_obj['points'] = 0.0
        answer_obj['time'] = float(seconds_total - seconds_left)

        if answer and not timedout:
            points_value = question['points_value']
            data['timedout'] = False
            answer_obj['answer'] = answer
            answer_obj['timedout'] = False
            if question.check_answer(answer):
                answer_obj['correct'] = True
                points = float(points_value * seconds_left)
                answer_obj['points'] = points
                coins = self.points_to_coins(points,
                                             seconds_total,
                                             points_value)
                data['points'] = points
                data['coins'] = coins

                # increment UserSettings
                user_settings = self.get_current_user_settings()
                user_settings['coins_total'] += coins
                user_settings.save()

            else:
                self.write({'incorrect': True})
                return
        else:
            answer_obj['timedout'] = True
            data['timedout'] = True
            data['correct_answer'] = question['correct']

        answer_obj.save()

        session['finish_date'] = datetime.datetime.utcnow()
        session.save()

        cache_key = 'questions_answered_stats:%s' % user['_id']
        self.redis.delete(cache_key)

        # if the last job was of the same category and location
        # then increment the number of coins
        for job in (self.db.Job
                    .find({'user': user['_id'],
                           'category': session['category'],
                           'location': session['location']})
                    .sort('add_date', 1)
                    .limit(1)):
            job['coins'] += data['coins']
            job.save()
            break
        else:
            job = self.db.Job()
            job['user'] = user['_id']
            job['coins'] = data['coins']
            job['category'] = session['category']
            job['location'] = session['location']
            job.save()

        if question['didyouknow']:
            data['didyouknow'] = self.render_didyouknow(question['didyouknow'])

        data['left'] = self._count_questions_left(
          category,
          user,
          current_location
        )

        self.write(data)

    def _count_questions_left(self, category, user, location):
        question_filter = {
          'location': location['_id'],
          'category': category['_id'],
        }
        past_question_ids = set()
        session_filter = {
          'user': user['_id'],
          'location': location['_id'],
          'category': category['_id'],
          'finish_date': {'$ne': None},
        }

        for other_session in self.db.QuestionSession.find(session_filter):
            for answer in self.db.SessionAnswer.find({'session': other_session['_id']}):
                past_question_ids.add(answer['question'])

        if past_question_ids:
            question_filter['_id'] = {'$nin': list(past_question_ids)}

        questions = self.db.Question.find(question_filter)
        return questions.count()

    def points_to_coins(self, points, seconds_total, points_value):
        max_ = seconds_total * points_value
        percentage = 100 * points / max_
        return int(percentage * self.PERCENTAGE_COINS_RATIO)


@route('/pinpoint.json$', name='pinpoint')
class PinpointHandler(AuthenticatedBaseHandler):

    # number that is multiplied with the percentage from perfection
    PERCENTAGE_COINS_RATIO = 1.4

    MIN_DISTANCE = 50.0
    NO_QUESTIONS = settings.PINPOINT_NO_QUESTIONS
    SECONDS = 10

    CATEGORY_NAME = u'Geographer'

    def calculate_points(self, miles, seconds_left):
        min_ = self.MIN_DISTANCE
        if miles < min_:
            p = (min_ - miles) / min_
        else:
            p = 0
        return seconds_left * p

    def points_to_coins(self, points):
        # max points is when you answer with 0 miles in 0 seconds
        # for every question
        max_ = self.NO_QUESTIONS * self.SECONDS * 1
        percentage = 100 * points / max_
        return int(percentage * self.PERCENTAGE_COINS_RATIO)

    def get(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        country = current_location['country']

        data = {}
        filter_ = {'country': country}
        if current_location['locality']:
            filter_['locality'] = current_location['locality']
        center = self.db.PinpointCenter.find_one(filter_)
        if not center and 'locality' in filter_:
            filter_.pop('locality')
            center = self.db.PinpointCenter.find_one(filter_)
        country = center['country']
        locality = getattr(center, 'locality', None)

        assert center

        data['center'] = {
          'sw': {
            'lat': center['south_west'][0],
            'lng': center['south_west'][1],
          },
          'ne': {
            'lat': center['north_east'][0],
            'lng': center['north_east'][1],
          }
        }
        data['no_questions'] = self.NO_QUESTIONS
        data['waiting_time'] = self.SECONDS

        if self.get_argument('next', None):
            session = (self.db.PinpointSession
                       .find_one({'user': user['_id'],
                                  'center': current_location['_id'],
                                  'finish_date': None}))
            if session is None:
                session = self.db.PinpointSession()
                session['user'] = user['_id']
                session['center'] = current_location['_id']
                session.save()

            for each in (self.db.PinpointAnswer
                         .find({'session': session['_id']})
                         .sort('add_date', -1)  # newest first
                         .limit(1)):
                previous_answer = each
                break
            else:
                previous_answer = None

            if previous_answer:
                if not previous_answer['answer']:
                    # no answer was sent, it must have timed out
                    previous_answer['timedout'] = True
                    previous_answer['points'] = 0.0
                    previous_answer.save()

            try:
                location = self._get_next_location(
                  session,
                  country,
                  locality=locality,
                  previous_location=(previous_answer['location']
                                     if previous_answer else None),
                )
            except NoLocationsError:
                self.write({'error': 'NOLOCATIONS'})
                return

            _no_answers = (self.db.PinpointAnswer
                           .find({'session': session['_id']})
                           .count())
            data['no_questions'] = {
              'total': self.NO_QUESTIONS,
              'number': _no_answers + 1,
              'last': _no_answers + 1 == self.NO_QUESTIONS,
            }
            if _no_answers < self.NO_QUESTIONS:
                answer = self.db.PinpointAnswer()
                answer['session'] = session['_id']
                answer['location'] = location['_id']
                answer.save()

                data['question'] = {
                  'name': location['city'],
                  'id': str(location['_id']),
                  'seconds': self.SECONDS,
                }
            else:
                self.write({'error': 'ALREADYSENTALLLOCATIONS'})
                return
        else:
            # close any unfinished sessions
            for session in (self.db.PinpointSession
                             .find({'user': user['_id'],
                                    'center': current_location['_id'],
                                    'finish_date': None})):
                # XXX: should I just delete them?
                session['finish_date'] = datetime.datetime.utcnow()
                session.save()

        self.write(data)

    def _get_next_location(self, session, country,
                           locality=None,
                           allow_repeats=False,
                           previous_location=None):
        filter_ = {
          'country': country,
        }
        if locality:
            filter_['locality'] = locality
        if previous_location:
            if not isinstance(previous_location, ObjectId):
                previous_location = previous_location['_id']
            filter_['_id'] = {'$ne': previous_location}

        if not allow_repeats:
            past_location_ids = set()
            for a in self.db.PinpointAnswer.find({'session': session['_id']}):
                past_location_ids.add(a['location'])
            if past_location_ids:
                if '_id' in filter_:
                    past_location_ids.add(filter_['_id']['$ne'])
                filter_['_id'] = {'$nin': list(past_location_ids)}
        locations = self.db.Location.find(filter_)
        count = locations.count()
        if not count:
            if allow_repeats:
                raise NoLocationsError("Not enough locations")
            return self._get_next_location(session, country,
                                           locality=locality,
                                           allow_repeats=True)

        nth = random.randint(0, count - 1)
        for location in locations.limit(1).skip(nth):
            return location

    def post(self):
        #stop_time = datetime.datetime.utcnow()
        user = self.get_current_user()
        center = self.get_current_location(user)

        data = {}

        if self.get_argument('finish', None):
            session, = (self.db.PinpointSession
                        .find({'user': user['_id'],
                               'center': center['_id']})
                        .sort('add_date', -1)  # newest first
                        .limit(1))
            session['finish_date'] = datetime.datetime.utcnow()
            session.save()

            last_answer, = (self.db.PinpointAnswer
                            .find({'session': session['_id']})
                            .sort('add_date', -1)
                            .limit(1))
            if not last_answer['answer']:
                last_answer['timedout'] = True
                last_answer['points'] = 0.0
                last_answer.save()

            total_points = 0.0
            summary = []

            for answer in (self.db.PinpointAnswer
                           .find({'session': session['_id']})
                           .sort('add_date', 1)):
                total_points += answer['points']
                location = (self.db.Location
                            .find_one({'_id': answer['location']}))
                summary.append({
                  'city': location['city'],
                  'time': (not answer['timedout']
                           and round(answer['time'], 1)
                           or None),
                  'points': round(answer['points'], 1),
                  'miles': (not answer['timedout']
                            and round(answer['miles'], 1)
                            or None),
                  'timedout': answer['timedout'],
                })
            data['summary'] = summary

            coins = self.points_to_coins(total_points)
            user_settings = self.get_current_user_settings()
            user_settings['coins_total'] += coins
            user_settings.save()

            category = self.db.Category.find_one({'name': self.CATEGORY_NAME})
            if not category:
                category = self.db.Category()
                category['name'] = self.CATEGORY_NAME
                category.save()

            job = self.db.Job()
            job['user'] = user['_id']
            job['coins'] = coins
            job['category'] = category['_id']
            job['location'] = center['_id']
            job.save()

            data['results'] = {
              'total_points': round(total_points, 1),
              'coins': coins,
            }

        else:

            guess = {
              'lat': float(self.get_argument('lat')),
              'lng': float(self.get_argument('lng'))
            }
            session, = (self.db.PinpointSession
                        .find({'user': user['_id'],
                               'center': center['_id'],
                               'finish_date': None})
                        .sort('add_date', -1)  # newest first
                        .limit(1))
            answer, = (self.db.PinpointAnswer
                       .find({'session': session['_id']})
                       .sort('add_date', -1)  # newest first
                       .limit(1))
            correct_location = (self.db.Location
                                .find_one({'_id': answer['location']}))
            assert correct_location
            correct_position = {
              'lat': correct_location['lat'],
              'lng': correct_location['lng']
            }

            distance = calculate_distance(guess, correct_position)
            data['miles'] = int(distance.miles)

            data['time'] = float(self.get_argument('time'))

            time_left = float(self.SECONDS - data['time'])
            points = self.calculate_points(distance.miles, time_left)

            data['points'] = round(points, 1)
            data['correct_position'] = correct_position
            answer['answer'] = (guess['lat'], guess['lng'])
            answer['time'] = round(data['time'], 2)
            answer['points'] = round(points, 2)
            answer['miles'] = distance.miles
            answer['timedout'] = False
            answer.save()

        self.write(data)




@route('/airport.json$', name='airport')
class AirportHandler(AuthenticatedBaseHandler,
                     FlightFinderMixin,
                     FlagMixin):

    def get(self):
        user = self.get_current_user()
        user_settings = self.get_current_user_settings(user)
        current_location = self.get_current_location(user)
        data = {
          'airport_name': current_location['airport_name'],
        }
        only_affordable = self.get_argument('only_affordable', False)
        ticket_progress = self.get_argument('ticket_progress', False)
        ticket_progress_min = float(self.get_argument('ticket_progress_min', 50.0))

        destinations = self.get_destinations(
            user,
            user_settings,
            current_location,
            only_affordable=only_affordable,
            ticket_progress=ticket_progress,
            ticket_progress_min=ticket_progress_min,
        )
        data['destinations'] = destinations
        for destination in destinations:
            flag = self.get_flag(destination, 16)
            if flag:
                destination['flag'] = flag
        data['for_amount'] = user_settings['coins_total']
        self.write(data)



@route('/fly.json$', name='fly')
class FlyHandler(AirportHandler):

    def get(self):
        user = self.get_current_user()
        route = self.get_argument('route')
        # use [0-9] only for the Nomansland thing
        try:
            from_, to = re.findall('[0-9A-Z]{3}', route)
        except ValueError:
            self.write({'error': 'INVALIDROUTE'})
            return
        from_ = self.db.Location.find_one({'code': from_})
        if not from_:
            self.write({'error': 'INVALIDAIRPORT'})
            return
        to = self.db.Location.find_one({'code': to})
        if not to:
            self.write({'error': 'INVALIDAIRPORT'})
            return
        if from_ == to:
            self.write({'error': 'INVALIDROUTE'})
            return
        flight = self.db.Flight.find_one({
          'user': user['_id'],
          'from': from_['_id'],
          'to': to['_id'],
        })
        if not flight:
            self.write({'error': 'INVALIDROUTE'})
            return

        data = {
          'from': {
            'lat': from_['lat'], 'lng': from_['lng']
          },
          'to': {
            'lat': to['lat'], 'lng': to['lng']
          },
          'miles': calculate_distance(from_, to).miles,
        }
        self.write(data)

    def post(self):
        _id = self.get_argument('id')
        try:
            location = self.db.Location.find_one({'_id': ObjectId(_id)})
            assert location
        except (InvalidId, AssertionError):
            raise tornado.web.HTTPError(400, 'Invalid id')
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        if location == current_location:
            self.write({'error': 'FLIGHTALREADYTAKEN'})
            return
        distance = calculate_distance(current_location, location)
        cost = self.calculate_cost(distance.miles, user)
        state = self.get_state()
        if cost > state['user']['coins_total']:
            self.write({'error': 'CANTAFFORD'})
            return

        # make the transaction
        user_settings = self.get_current_user_settings(user)
        user_settings['coins_total'] -= cost
        miles_total_before = user_settings['miles_total']
        user_settings['miles_total'] += distance.miles
        miles_total_after = user_settings['miles_total']
        user_settings.save()
        user['current_location'] = location['_id']
        user.save()

        flight = self.db.Flight()
        flight['user'] = user['_id']
        flight['from'] = current_location['_id']
        flight['to'] = location['_id']
        flight['miles'] = distance.miles
        flight.save()

        transaction = self.db.Transaction()
        transaction['user'] = user['_id']
        transaction['cost'] = cost
        transaction['flight'] = flight['_id']
        transaction.save()
        if current_location['code'] == self.NOMANSLAND['code']:
            # you have left the tutorial
            if not self.has_tutorial_award(user):
                data_ = {
                  #'perfect': percentage == 100.0,
                  #'percentage': percentage,
                  #'coins': coins,
                }
                reward = 50
                award = self.create_tutorial_award(
                  user,
                  reward,
                  data_
                )
                user_settings['coins_total'] += reward
                user_settings.save()
        else:
            if miles_total_after > 10000 and miles_total_before < 10000:
                if not self.has_10k_award(user):
                    reward = 75
                    data_ = {
                      'from': unicode(current_location),
                      'to': unicode(location)
                    }
                    self.create_10k_award(user, current_location,
                                          reward, data_)
            elif miles_total_after > 50000 and miles_total_before < 50000:
                if not self.has_50k_award(user):
                    reward = 150
                    data_ = {
                      'from': unicode(current_location),
                      'to': unicode(location)
                    }
                    self.create_50k_award(user, current_location,
                                          reward, data_)
            elif miles_total_after > 100000 and miles_total_before < 100000:
                if not self.has_100k_award(user):
                    reward = 500
                    data_ = {
                      'from': unicode(current_location),
                      'to': unicode(location)
                    }
                    self.create_100k_award(user, current_location,
                                           reward, data_)

        data = {
          'from_code': current_location['code'],
          'to_code': location['code'],
          'cost': cost,
        }
        self.write(data)


@route('/state.json$', name='state')
class StateHandler(BaseHandler):

    def get(self):
        state = self.get_state()
        self.write({'state': state})


class BaseAuthHandler(BaseHandler):

    INVITATION_AWARD = 100

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
        subject = "[Around the world] New user!"
        email_body = "%s %s\n" % (user.first_name, user.last_name)
        email_body += "%s\n" % user.email
        if extra_message:
            email_body += '%s\n' % extra_message
        logging.info(subject)
        logging.info(email_body)
        return
        send_email(self.application.settings['email_backend'],
                   subject,
                   email_body,
                   self.application.settings['admin_emails'][0],
                   self.application.settings['admin_emails'],
                   )

    def make_username(self, first_name, last_name):
        def simple(s):
            return s.lower().replace(' ', '').replace('-', '')
        return '%s%s' % (simple(first_name), simple(last_name))

    def post_login_successful(self, user, previous_user=None):
        """executed by the Google, Twitter and Facebook
        authentication handlers"""
        if not user['current_location']:
            nomansland = self.db.Location.find_one({'city': 'Nomansland'})
            if not nomansland:
                nomansland = self.db.Location()
                nomansland['city'] = self.NOMANSLAND['city']
                nomansland['country'] = self.NOMANSLAND['country']
                nomansland['airport_name'] = self.NOMANSLAND['airport_name']
                nomansland['code'] = self.NOMANSLAND['code']
                nomansland['available'] = False
                nomansland['lng'] = self.NOMANSLAND['lng']
                nomansland['lat'] = self.NOMANSLAND['lat']
                nomansland.save()

            tutorial = self.db.Category.find_one({'name': 'Tutorial'})
            if not tutorial:
                tutorial = self.db.Category()
                tutorial['name'] = u'Tutorial'
                tutorial.save()

            user['current_location'] = nomansland['_id']
            user.save()
        try:
            self._post_login_successful(user, previous_user=previous_user)
        except:  # pragma: no cover
            raise
            logging.error("Failed to post login successful user",
                          exc_info=True)

    def _post_login_successful(self, user, previous_user=None):

        if user['email']:
            regex = re.compile(re.escape(user['email']), re.I)
            invitation = (self.db.Invitation
                          .find_one({'email': regex,
                                     'signedup_user': None}))
            if invitation:
                invitation['signedup_user'] = user['_id']
                invitation.save()

                inviter = self.db.User.find_one({'_id': invitation['user']})
                inviter_settings = self.get_user_settings(inviter)
                inviter_settings.coins_total += self.INVITATION_AWARD
                inviter_settings.save()

                category = self.db.Category.find_one({'name': u'Recruiter'})
                if not category:
                    category = self.db.Category()
                    category['name'] = u'Recruiter'
                    category['manmade'] = False
                    category.save()

                job = self.db.Job()
                job['user'] = inviter['_id']
                job['coins'] = self.INVITATION_AWARD
                job['category'] = category['_id']
                job['location'] = inviter['current_location']
                job.save()

                self.email_inviter(inviter, invitation, user)

        friendship_invites = self.get_pending_friendship_invites()
        if friendship_invites:
            for token in friendship_invites:
                from_user = self.db.User.find_one({'_id': token['user']})
                assert from_user['_id'] != user['_id'], user['_id']
                friendship1 = self.db.Friendship()
                friendship1['user'] = from_user['_id']
                friendship1['to'] = user['_id']
                friendship1['mutual'] = True
                friendship1.save()

                friendship2 = self.db.Friendship()
                friendship2['user'] = user['_id']
                friendship2['to'] = from_user['_id']
                friendship2['mutual'] = True
                friendship2.save()

                token.delete()

        if previous_user and previous_user['anonymous'] and not user['anonymous']:
            self._transferUser(previous_user, user)
            if not self.has_signin_award(user):
                data = {

                }
                reward = 100
                award = self.create_signin_award(
                  user,
                  self.get_current_location(user),
                  reward,
                  data
                )
                user_settings = (self.db.UserSettings
                                 .find_one({'user': user['_id']}))
                user_settings['coins_total'] += reward
                user_settings.save()

    def _transferUser(self, old, new):
        models = (
          self.db.Flight,
          self.db.Transaction,
          self.db.Job,
          (self.db.Question, 'author'),
          self.db.QuestionSession,
          self.db.PinpointSession,
          self.db.Feedback,
          self.db.Invitation,
          self.db.LocationMessage,
          self.db.QuestionRating,
          self.db.Award,
          self.db.Deposit,
          self.db.InterestEarning,
        )

        for each in models:
            if isinstance(each, tuple):
                model, key = each
            else:
                model, key = each, 'user'

            for each in model.find({key: old['_id']}):
                each[key] = new['_id']
                each.save()

        new['current_location'] = old['current_location']
        new.save()

        # transfer or merge UserSettings
        new_usersettings, = self.db.UserSettings.find({'user': new['_id']})
        old_usersettings, = self.db.UserSettings.find({'user': old['_id']})
        fmt = '%Y%m%d%H%M%S'
        if (new_usersettings['add_date'].strftime(fmt) ==
            new_usersettings['add_date'].strftime(fmt) and
            new_usersettings['coins_total'] == 0):
            # it's new, then transfer
            new_usersettings.delete()
            old_usersettings['user'] = new['_id']
            old_usersettings['was_anonymous'] = True
            old_usersettings.save()
        else:
            new_usersettings['coins_total'] += old_usersettings['coins_total']
            new_usersettings['miles_total'] += old_usersettings['miles_total']
            old_usersettings.delete()

        old.delete()

    def email_inviter(self, inviter, invitation, user):
        if not inviter['email']:
            return
        to = inviter['email']
        from_ = getattr(settings, 'NOREPLY_EMAIL', None)
        if not from_:
            from_ = 'noreply@%s' % self.request.host
        subject = (u"Congratulations! %s has now joined %s" %
                   (self.get_name(user), settings.PROJECT_TITLE))
        body = []
        body = self.render_string('invitation_complete.txt', **{
            'inviter_name': inviter['first_name'] and inviter['first_name'] or inviter['username'],
            'invitation': invitation,
            'name': self.get_name(user),
            'coins': self.INVITATION_AWARD,
            'total_earned': self.get_total_earned(inviter)['coins'],
        })
        send_email(
            self.application.settings['email_backend'],
            subject,
            body,
            from_,
            [to]
        )


@route('/auth/anonymous/', name='auth_anonymous')
class AnonymousAuthHandler(BaseAuthHandler):

    def post(self):
        user = self.db.User()
        user.username = self._anonymous_username()
        user.anonymous = True
        user.set_password(unicode(uuid.uuid4()))
        user.save()

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.save()

        old_user = self.get_current_user()
        self.post_login_successful(user, previous_user=old_user)
        self.set_secure_cookie("user", str(user._id), expires_days=1)
        self.redirect(self.get_next_url())

    def _anonymous_username(self):
        prefix = u'anonymous'

        def mk():
            return prefix + uuid.uuid4().hex[:4]

        name = mk()
        while self.db.User.find({'username': name}).count():
            name = mk()
        return name


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
            self.write("""<html>Error. Unable to log in.
            Did you not allow any login details to be shared?</html>""")
            self.finish()
            return
            #raise HTTPError(500, "Google auth failed")
        if not user.get('email'):
            raise HTTPError(500, "No email provided")

#        user={u'username': u'martin', u'superuser': False, u'first_name': u'Martin', u'last_name': u'Seehuusen', u'anonymous': False, u'add_date': datetime.datetime(2012, 6, 11, 0, 51, 4, 40000), u'password': u'5c0a5392-063d-433c-842d-43d01a148f47', u'modify_date': datetime.datetime(2012, 6, 11, 2, 7, 24, 226000), u'current_location': ObjectId('4f3d6fc974a1f83646000001'), u'_id': ObjectId('4fd540f874a1f866e7000079'), u'email': u'martin@msdesigns.com.au'}
#        user={u'username': u'ashleynbe', u'first_name': u'Ashley', u'last_name': u'Bengtsson', u'email': u'ashleynbe@gmail.com'}

        user_struct = user
        #locale = user.get('locale')  # not sure what to do with this yet
        first_name = user.get('first_name')
        last_name = user.get('last_name')
        username = user.get('username')
        email = user['email']
        if not username:
            username = email.split('@')[0]

        user = self.db.User.one({'username': username})
        if not user:
            user = self.db.User.one({'email': email})
            if user is None:
                user = (self.db.User.find_one({
                          'email': re.compile(re.escape(email), re.I)}))

        if not user:
            # create a new account
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name

            user.set_password(unicode(uuid.uuid4()))
            user.save()
            self.notify_about_new_user(user,
                                       extra_message="Used Google OpenID")

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings.google = user_struct
        if user.email:
            user_settings.email_verified = user.email
        user_settings.save()

        old_user = self.get_current_user()
        self.post_login_successful(user, previous_user=old_user)
        self.set_secure_cookie("user", str(user._id), expires_days=300)
        self.redirect(self.get_next_url())


@route('/auth/twitter/', name='auth_twitter')
class TwitterAuthHandler(BaseAuthHandler, tornado.auth.TwitterMixin):
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        elif self.get_argument('denied', None):
            self.redirect('/')
            return
        self.authenticate_redirect()

    def _on_auth(self, user_struct):
        if not user_struct:
            raise HTTPError(500, "Twitter auth failed")
        if not (user_struct.get('email') or user_struct.get('username')):
            raise HTTPError(500, "No email or username provided")
        username = user_struct.get('username')
        if user_struct.get('first_name') or user_struct.get('last_name'):
            first_name = user_struct.get('first_name', u'')
            last_name = user_struct.get('last_name', u'')
        else:
            first_name = user_struct.get('name').split(None, 1)[0]
            try:
                last_name = user_struct.get('name').split(None, 1)[1]
            except IndexError:
                last_name = u''
        email = user_struct.get('email', u'')

        if not username:
            username = email.split('@')[0]

        user = self.db.User.one({'username': username})
        if not user and email:
            user = self.db.User.one({'email': email})
            if user is None:
                user = (self.db.User.find_one({
                          'email': re.compile(re.escape(email), re.I)}))

        if not user:
            # create a new account
            user = self.db.User()
            user.username = username
            user.email = email
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.set_password(unicode(uuid.uuid4()))
            user.save()
            self.notify_about_new_user(user, extra_message="Used Twitter")
        else:
            if first_name:
                user['first_name'] = first_name
            if last_name:
                user['last_name'] = last_name
            user.save()

        user_settings = self.get_user_settings(user)
        if not user_settings:
            user_settings = self.create_user_settings(user)
        user_settings['twitter'] = user_struct
        user_settings.save()

        old_user = self.get_current_user()
        self.post_login_successful(user, previous_user=old_user)
        self.set_secure_cookie("user", str(user._id), expires_days=300)
        self.redirect(self.get_next_url())


@route(r'/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def post(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())

    def get(self):  # not sure if we need this other than for debugging
        self.clear_all_cookies()
        self.redirect(self.get_next_url())


@route(r'/iplookup/', name='iplookup')
class IPLookupHandler(BaseHandler):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        ip = self.get_current_ip()
        if not ip:
            self.write({})
            self.finish()
            return
        cache_key = 'iplookup-%s' % ip
        value = self.redis.get(cache_key)
        if value:
            data = tornado.escape.json_decode(value)
        else:
            # see https://github.com/fiorix/freegeoip/blob/master/README.rst
            url = 'http://freegeoip.net/json/%s' % ip
            http_client = tornado.httpclient.AsyncHTTPClient()
            response = yield tornado.gen.Task(http_client.fetch, url)
            data = {}
            if response.code == 200:
                struct = tornado.escape.json_decode(response.body)
                data['lat'] = struct['latitude']
                data['lng'] = struct['longitude']
                self.redis.setex(
                  cache_key,
                  tornado.escape.json_encode(data),
                  ONE_WEEK
                )
            else:
                logging.warn("%s: %r" % (response.code, response.body))
        self.write(data)
        self.finish()


@route('/test.html')
class TestHandler(BaseHandler):
    def get(self):
        self.render('test.html')


@route('/welcome.json$', name='welcome')
class WelcomeHandler(AuthenticatedBaseHandler):

    def get(self):
        if self.get_argument('get') == 'stats':
            stats = self.get_stats(self.get_current_user())
            self.write(stats)

    def get_stats(self, user):
        data = {}
        user_search = {'user': user['_id']}
        user_settings = self.get_current_user_settings(user)
        data['coins_total'] = user_settings['coins_total']
        data['miles_total'] = user_settings['miles_total']

        spent_total = 0
        spent_flights = 0
        for transaction in (self.db.Transaction.collection
                            .find(user_search,
                                  ('cost', 'flight'))):
            spent_total += transaction['cost']
            if transaction['flight']:
                spent_flights += transaction['cost']
        data['spent_total'] = spent_total
        data['spent_flights'] = spent_flights

        total_earned = self.get_total_earned(user)
        earned_jobs = total_earned['jobs']
        earned_questions = total_earned['questions']

        invitations = self.db.Invitation.find(user_search).count()
        data['invitations'] = invitations
        invitations = (self.db.Invitation
                       .find(dict(user_search, signedup_user={'$ne': None}))
                       .count())
        data['invitations_signedup'] = invitations

        location_messages = self.db.LocationMessage.find(user_search).count()
        data['location_messages'] = location_messages

        authored_questions = (self.db.Question
                              .find({'author': user['_id']})
                              .count())
        data['authored_questions'] = authored_questions
        authored_questions = (self.db.Question
                              .find({'author': user['_id'],
                                     'published': True})
                              .count())
        data['authored_questions_published'] = authored_questions

        earned_total = earned_jobs + earned_questions
        data['earned_questions'] = earned_questions
        data['earned_jobs'] = earned_jobs
        data['earned_total'] = earned_total

        _tos = set()
        for flight in (self.db.Flight.collection
                       .find(user_search, ('to',))):
            _tos.add(flight['to'])
        data['visited_cities'] = len(_tos)
        _available_cities = (self.db.Location
                             .find({'available': True})
                             .count())
        data['cities_max'] = _available_cities

        _available_questions = (self.db.Question
                             .find({'published': True})
                             .count())
        data['questions_max'] = _available_questions
        data.update(self.get_questions_answered_stats(user))
        return data

    def get_questions_answered_stats(self, user):
        cache_key = 'questions_answered_stats:%s' % user['_id']
        data = self.redis.get(cache_key)
        if data:
            data = tornado.escape.json_decode(data)
        else:
            data = self._get_questions_answered_stats(user)
            self.redis.setex(
                cache_key,
                tornado.escape.json_encode(data),
                ONE_DAY
            )
        return data

    def _get_questions_answered_stats(self, user):
        # actually do the queries
        user_search = {'user': user['_id']}
        sessions = 0
        answers = 0
        answers_right = 0
        _answered_questions = set()
        for session in (self.db.QuestionSession.collection
                        .find(dict(user_search, finish_date={'$ne': None}),
                              ('_id',))):
            sessions += 1
            for answer in (self.db.SessionAnswer.collection
                           .find({'session': session['_id']},
                                 ('correct', 'question'))):
                answers += 1
                if answer['correct']:
                    answers_right += 1
                _answered_questions.add(answer['question'])
        return {
            'question_sessions': sessions,
            'question_answers': answers,
            'question_answers_right': answers_right,
            'question_answered_unique_questions': len(_answered_questions)
        }


@route('/feedback.json$', name='feedback')
class FeedbackHandler(AuthenticatedBaseHandler):

    def post(self):
        what = self.get_argument('what')
        comment = self.get_argument('comment')
        email = self.get_argument('email', u'')
        user = self.get_current_user()
        location = self.get_current_location()

        feedback = self.db.Feedback()
        feedback['what'] = what
        feedback['comment'] = comment
        if email:
            feedback['email'] = email
        if user:
            feedback['user'] = user['_id']
            feedback['location'] = location['_id']
        feedback.save()

        try:
            admin_url = '%s://%s' % (self.request.protocol,
                                     self.request.host)
            admin_url += self.reverse_url('admin_feedback_reply', feedback['_id'])
            body = self.render_string("feedback_posted.txt", **{
              'feedback': feedback,
              'feedback_location': location,
              'feedback_user': user,
              'admin_url': admin_url,
            })
            send_email(
              self.application.settings['email_backend'],
              "New piece of feedback",
              body,
              self.application.settings['admin_emails'][0],
              self.application.settings['admin_emails'],
              )
        except:
            logging.error("Failed to send email",
                          exc_info=True)

        self.write({'ok': True})


@route('/questionwriter.json', name='questionwriter')
class QuestionWriterHandler(AuthenticatedBaseHandler, PictureThumbnailMixin):

    # how many coins do you earn per play
    COINS_EARNING_VALUE = 1

    def get(self):
        data = {}
        categories = []
        user = self.get_current_user()
        current_location = self.get_current_location(user)

        if self.get_argument('question_id', None):
            question = self._get_question(self.get_argument('question_id'),
                                          user, current_location)
            data['text'] = question['text']
            data['correct'] = question['correct']
            data['alternatives'] = question['alternatives']
            if data['correct'] in data['alternatives']:
                data['alternatives'].remove(data['correct'])
            if question['published']:
                data['earned'] = self._get_earned(question)
            else:
                data['earned'] = None
            data['published'] = question['published']
            data['points_value'] = question['points_value']
            if data['points_value'] == 1:
                data['points_value'] = '%s (easy)' % data['points_value']
            elif data['points_value'] == 3:
                data['points_value'] = '%s (medium)' % data['points_value']
            elif data['points_value'] == 5:
                data['points_value'] = '%s (hard)' % data['points_value']
            category, = self.db.Category.find({'_id': question['category']})
            data['category'] = category['name']
            data['didyouknow'] = question['didyouknow']
            _ratings = self._get_rating_total(question)
            if _ratings['count']['all']:  # any?
                data['ratings'] = {'average': _ratings['average'],
                                   'count': _ratings['count']}

            if question.has_picture():
                picture = question.get_picture()
                uri, (width, height) = self.get_thumbnail(picture, (250, 250))

                url = self.static_url(uri.replace('/static/', ''))
                data['picture'] = {
                  'url': url,
                  'width': width,
                  'height': height,
                }

            self.write(data)
            return

        for each in (self.db.Question
                     .find({'location': current_location['_id']})
                     .distinct('category')):
            category, = self.db.Category.find({'_id': each})
            categories.append({
              'value': str(category['_id']),
              'label': category['name']
            })
        data['categories'] = categories
        data['filepicker_key'] = settings.FILEPICKER_API_KEY
        data['questions'] = self._get_questions(user, current_location)
        self.write(data)

    def _get_question(self, question_id, user, current_location):
        filter_ = {'_id': ObjectId(question_id),
                   'author': user['_id'],
                   'location': current_location['_id']}
        question, = self.db.Question.find(filter_)
        return question

    def _get_questions(self, user, location):
        filter_ = {'author': user['_id'],
                   'location': location['_id']}
        questions = []
        _categories = {}
        for each in self.db.Question.find(filter_).sort('add_date', -1):
            if each['category'] not in _categories:
                category, = self.db.Category.find({'_id': each['category']})
                _categories[each['category']] = category['name']
            question = {
              'id': str(each['_id']),
              'text': each['text'],
              'published': each['published'],
              'earned': 0,
              'category': _categories[each['category']],
            }
            if each['published']:
                question['earned'] = self._get_earned(each)
            questions.append(question)
        return questions

    def _get_rating_total(self, question):
        rating_total = (self.db.QuestionRatingTotal
                        .find_one({'question': question['_id']}))
        if not rating_total:
            data = question.calculate_ratings()
            rating_total = self.db.QuestionRatingTotal()
            rating_total['question'] = question['_id']
            rating_total['average']['all'] = data['average']['all']
            rating_total['average']['right'] = data['average']['right']
            rating_total['average']['wrong'] = data['average']['wrong']
            rating_total['count']['all'] = data['count']['all']
            rating_total['count']['right'] = data['count']['right']
            rating_total['count']['wrong'] = data['count']['wrong']
            rating_total.save()
        return rating_total

    def _get_earned(self, question):
        # XXX this could be replaced with a sum function once
        # mongo fully supports it (v 2.1)
        c = 0
        for each in (self.db.QuestionAnswerEarning
                     .find({'question': question['_id']},
                           ('coins',))):
            c += each['coins']
        return c

    def post(self):
        current_user = self.get_current_user()
        current_location = self.get_current_location(current_user)

        errors = {}
        text = self.get_argument('text', '').strip()
        if not text:
            errors['text'] = "Empty"
        elif not text[-1] == '?':
            errors['text'] = "Must be a question"
        correct = self.get_argument('correct', '').strip()
        if not correct:
            errors['correct'] = "Empty"
        alternatives = [x.strip() for x in
                        self.get_argument('alternatives', '').splitlines()
                        if x.strip()]
        if not alternatives:
            errors['alternatives'] = 'Empty'

        if errors:
            self.write(dict(errors=errors))
            return

        didyouknow = self.get_argument('didyouknow', u'').strip()
        category_id = self.get_argument('category')
        category, = self.db.Category.find({'_id': ObjectId(category_id)})
        points_value = int(self.get_argument('points_value'))
        assert points_value >= 1
        assert points_value <= Question.HIGHEST_POINTS_VALUE

        if self.get_argument('file_url', None):
            file_url = self.get_argument('file_url')
            assert os.path.isfile(file_url)
        else:
            file_url = None

        question = self.db.Question()
        question['text'] = text
        question['correct'] = correct
        question['alternatives'] = [correct] + alternatives
        question['author'] = current_user['_id']
        question['seconds'] = 10
        question['location'] = current_location['_id']
        question['category'] = category['_id']
        question['published'] = False
        question['points_value'] = points_value
        question['didyouknow'] = didyouknow
        question.save()

        if file_url:
            picture = self.db.QuestionPicture()
            picture['question'] = question['_id']
            picture.save()
            type_, __ = mimetypes.guess_type(os.path.basename(file_url))
            with open(file_url, 'rb') as source:
                with picture.fs.new_file('original') as f:
                    f.content_type = type_
                    f.write(source.read())

        try:
            self._notify_about_new_question(
              question,
              current_user,
              current_location
            )
        except Exception:
            logging.error("Failed to notify about new question",
                          exc_info=True)

        self.write(dict(question_id=str(question['_id'])))

    def _notify_about_new_question(self, question, user, location):
        out = StringIO()
        subject = "New question by %s in %s" % (user['username'], location)
        url = self.reverse_url('admin_question', question['_id'])

        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        url = base_url + url
        out.write('Question:\n')
        out.write('%s\n\n' % question['text'])
        out.write('URL:\n')
        out.write('%s\n\n' % url)

        try:
            body = out.getvalue()
            send_email(
              self.application.settings['email_backend'],
              subject,
              body,
              self.application.settings['admin_emails'][0],
              self.application.settings['admin_emails'],
            )
        except:
            logging.error("Failed to send email",
                          exc_info=True)


@route('/questionwriter-check.json', name='questionwriter_check')
class QuestionFileURLCheckHandler(AuthenticatedBaseHandler,
                                  PictureThumbnailMixin):

    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        file_url = self.get_argument('check_file_url')
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = yield tornado.gen.Task(http_client.fetch, file_url)
        if response.code == 200:
            file_path = os.path.join(self.get_save_path(), str(uuid.uuid4()))
            with open(file_path, 'wb') as f:
                f.write(response.body)
            try:
                image = Image.open(file_path)

                if image.format == 'PNG':
                    new_file_path = file_path + '.png'
                    os.rename(file_path, new_file_path)
                elif image.format == 'JPEG':
                    new_file_path = file_path + '.jpg'
                    os.rename(file_path, new_file_path)
                else:
                    new_file_path = None

                if new_file_path:
                    #uri, (width, height) =\
                    # self.get_thumbnail(picture, (250, 250))
                    static_path = self.static_url(new_file_path
                      .replace(self.application.settings['static_path'] + '/',
                               ''))
                    self.write({'url': new_file_path,
                                'static_url': static_path})
                else:
                    self.write({'error': 'Picture has to be a .png or .jpg'})

            except IOError:
                self.write({'error': 'File upload was not a picture'})

        else:
            self.write({'error': 'Could not make a thumbnail out of it'})

        self.finish()

    def get_save_path(self):
        static_path = self.application.settings['static_path']
        f = os.path.join(static_path, 'tmp_uploads')
        if not os.path.isdir(f):
            os.mkdir(f)
        today = datetime.datetime.utcnow()
        f = os.path.join(f, today.strftime('%Y'))
        if not os.path.isdir(f):
            os.mkdir(f)
        f = os.path.join(f, today.strftime('%m'))
        if not os.path.isdir(f):
            os.mkdir(f)
        f = os.path.join(f, today.strftime('%d'))
        if not os.path.isdir(f):
            os.mkdir(f)

        return f


@route('/errors/$', name='errors')
class ErrorsHandler(BaseHandler):

    def post(self):
        data = {}
        for key in self.request.arguments:
            data[key] = self.get_argument(key)

        self.write('OK')

        user = self.get_current_user()
        for error_event in (self.db.ErrorEvent.find()
                            .sort('add_date', -1)
                            .limit(1)):
            if (user and error_event['user'] == user['_id'] and
                error_event['url'] == data.get('url') and
                error_event['data'] == data):

                error_event['count'] += 1
                error_event.save()
                return

        error_event = self.db.ErrorEvent()
        if user:
            error_event['user'] = user['_id']
        error_event['data'] = data
        error_event['url'] = data.get('url')
        error_event.save()
        logging.warn("Saved ErrorEvent: %s", data)


@route('/awards.json$', name='awards')
class AwardsHandler(BaseHandler):

    def get(self):
        data = {}

        user = self.get_current_user()
        current_location = self.get_current_location(user)

        _locations = {}
        _categories = {}

        def describe_award(award):
            if award['location'] not in _locations:
                _locations[award['location']] = (
                    self.db.Location
                    .find_one({'_id': award['location']})['city']
                )
            if award['category'] and award['category'] not in _categories:
                _categories[award['category']] = unicode(
                    self.db.Category
                    .find_one({'_id': award['category']})
                )
            info = {
              'id': str(award['_id']),
              'description': award['description'],
              'location': _locations[award['location']],
              'category': award['category'] and _categories[award['category']] or None,
              'type': award['type'],
              'read': award['read'],
              'date': award['add_date'].strftime('%d %B %Y')
            }
            return info

        if self.get_argument('id', None):
            award = self._get_award(self.get_argument('id'))
            if not award:
                self.write({'error': 'INVALIDAWARD'})
                return
            was_unread = False
            if user and award['user'] == user['_id'] and not award['read']:
                award['read'] = True
                award.save()
                was_unread = True
            info = describe_award(award)

            info['was_unread'] = was_unread
            award_user = self.db.User.find_one({'_id': award['user']})
            if award_user['first_name']:
                name = u'%s %s' % (award_user['first_name'],
                                   award_user['last_name'])
                name = name.strip()
            elif award_user['anonymous'] and user:
                name = u"You"
            else:
                name = award_user['username']
            info['name'] = name
            if award['ambassador']:
                ambassador = self.db.User.find_one({'_id': award['ambassador']})
            else:
                # hackish exception
                ambassador = self.db.User.find_one({'username': 'peterbe'})

            ambassador = u'%s %s' % (ambassador['first_name'],
                                     ambassador['last_name'])
            ambassador = ambassador.strip()
            info['ambassador'] = ambassador

            info['long_description'] = self.get_long_description(
                award,
                award_user == user,
                name
            )
            info['uniqueness'] = self.get_uniqueness(award)
            data['award'] = info

        else:
            awards = []
            if user:
                for each in (self.db.Award.find({'user': user['_id']})
                              .sort('add_date', -1)):
                    awards.append(describe_award(each))
            data['awards'] = awards

        self.write(data)

    def get_uniqueness(self, award):
        users = self.db.User.find().count()
        filter_ = {
          'type': award['type']
        }
        if award.get('category'):
            filter_['category'] = award['category']
        if award['type'] == 'job' and award.get('location'):
            filter_['location'] = award['location']
        awards = self.db.Award.find(filter_).count()
        return 100. * awards / users

    def get_long_description(self, award, yours, name):
        data = award['data']
        if yours:
            name = 'You'
        desc = (
          "%s earned this award %s ago. "
          % (name,
             smartertimesince(award['add_date'], datetime.datetime.utcnow()))
        )
        if award['type'] == 'job':
            category = self.db.Category.find_one({'_id': award['category']})
            if category.name == u'Tutorial':
                desc += "%s completed the tutorial. " % name
            else:
                desc += "%s completed the award as %s" % (name, category.name)
                if data.get('percentage') == 100:
                    desc += " with perfect results. "
                else:
                    desc += ". "
        if award['reward']:
            if name == 'You':
                name = 'you'
            desc += ("As a reward %s earned an extra %s coins."
                      % (name, award['reward']))
        return desc

    def _get_award(self, _id):
        try:
            award = self.db.Award.find_one({'_id': ObjectId(_id)})
            assert award
        except:
            logging.error("Unable to find reward %r" % _id, exc_info=True)
            return
        return award


@route('/awards-tweet.json', name='awards_tweet')
class AwardsTweetHandler(AwardsHandler):


    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):
        award = self._get_award(self.get_argument('id'))
        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        url = base_url + '/awards,%s' % award['_id']

        short_url = award['data'].get('short_url')
        if not short_url:
            URL = 'https://www.googleapis.com/urlshortener/v1/url'
            http_client = tornado.httpclient.AsyncHTTPClient()
            body = tornado.escape.json_encode({'longUrl': url})
            response = yield tornado.gen.Task(http_client.fetch,
                URL,
                method="POST",
                headers={'Content-Type': 'application/json'},
                body=body
            )
            if response.code == 200:
                short_url = tornado.escape.json_decode(response.body)['id']
                award['data']['short_url'] = short_url
                award.save()
            else:
                logging.warning("Unable to short %s (%s, %r)" % (
                  url,
                  response.code,
                  response.body
                ))
                short_url = url

        self.write({
          'text': 'I was awarded the "%s" award on Around The World\n%s @ardthewrld' %
            (award['description'], short_url),
          'url': short_url,
        })
        self.finish()


@route('/banks.json', name='banks')
class BanksHandler(AuthenticatedBaseHandler, BankingMixin):

    def get(self):
        data = {}

        user = self.get_current_user()
        current_location = self.get_current_location(user)
        data['location_name'] = current_location['city']

        def describe_bank(bank):
            other_cities = []
            for each in (self.db.Bank.collection
                         .find({'name': bank['name']}, ('location',))):
                if each['location'] == bank['location']:
                    continue
                other_cities.append(
                  unicode(self.db.Location.find_one({'_id': each['location']}))
                )
            banks_same_name = [x['_id'] for x in
                               self.db.Bank.collection
                                .find({'name': bank['name']}, ('_id',))]
            deposits = (self.db.Deposit.collection
                        .find({'bank': {'$in': banks_same_name},
                               'user': user['_id']}))
            sum_ = sum(x['amount'] for x in deposits)
            deposits.rewind()
            info = {
              'id': str(bank['_id']),
              'name': bank['name'],
              'open': bank['open'],
              'default_interest_rate': bank['default_interest_rate'],
              'withdrawal_fee': bank['withdrawal_fee'],
              'deposit_fee': bank['deposit_fee'],
              'other_cities': other_cities,
              'has_account': deposits.count() > 0,
              'sum': int(sum_),
              'interest': int(round(self.calculate_compound_interest(deposits))),
            }
            return info

        if self.get_argument('id', None):
            bank = self._get_bank(self.get_argument('id'))
            if not bank:
                self.write({'error': 'INVALIDAWARD'})
                return
            data['bank'] = describe_bank(bank)
        else:
            available = (self.db.Bank
                     .find({'location': current_location['_id']})
                     .sort('name'))
            banks = []
            for bank in available:
                banks.append(describe_bank(bank))
            data['banks'] = banks
        self.write(data)

    def _get_bank(self, _id):
        try:
            bank = self.db.Bank.find_one({'_id': ObjectId(_id)})
            assert bank
        except:
            logging.error("Unable to find bank %r" % _id, exc_info=True)
            return
        return bank

    def post(self):
        amount = self.get_argument('amount')
        action = self.get_argument('action')

        user = self.get_current_user()
        current_location = self.get_current_location(user)
        user_settings = self.get_user_settings(user)

        try:
            _id = self.get_argument('id')
            bank = self.db.Bank.find_one({'_id': ObjectId(_id)})
            assert bank
        except (InvalidId, AssertionError):
            raise tornado.web.HTTPError(400, 'Invalid bank')
        if bank['location'] != current_location['_id']:
            raise tornado.web.HTTPError(400, 'Invalid bank location')

        data = {}
        errors = {}
        try:
            amount = int(amount.replace(',', ''))
            assert amount > 0
        except:
            errors['amount'] = "Must be a number greater than zero"
        # check that you have enough money to deposit
        if action in ('open', 'deposit'):
            if bank['deposit_fee'] > user_settings['coins_total']:
                errors['deposit_fee'] = "Not enough coins to deposit"

            if 'amount' not in errors:
                # check the amount
                if amount > user_settings['coins_total']:
                    errors['amount'] = "You only have %s coins" % user_settings['coins_total']
        elif action == 'withdraw':
            banks_same_name = [x['_id'] for x in
                               self.db.Bank.collection
                                .find({'name': bank['name']}, ('_id',))]
            deposits = (self.db.Deposit.collection
                        .find({'bank': {'$in': banks_same_name},
                               'user': user['_id']}))
            balance = sum(x['amount'] for x in deposits)
            deposits.rewind()
            interest = self.calculate_compound_interest(deposits)
            total = balance + interest
            if amount > total:
                errors['amount'] = 'Not enough coins to make this withdrawal'
        else:
            raise tornado.web.HTTPError(400, 'Invalid bank action')

        if not errors:
            # go ahead and do it
            if action == 'withdraw':
                user_settings['coins_total'] += amount
                user_settings['coins_total'] -= bank['withdrawal_fee']
                user_settings.save()
                left = total - amount
                if interest:
                    interest_earning = self.db.InterestEarning()
                    interest_earning['user'] = user['_id']
                    interest_earning['bank'] = bank['_id']
                    interest_earning['coins'] = int(interest)
                    interest_earning.save()

                for each in (self.db.Deposit
                             .find({'bank': {'$in': banks_same_name},
                                    'user': user['_id']})):
                    each.delete()
                if left:
                    deposit = self.db.Deposit()
                    deposit['bank'] = bank['_id']
                    deposit['user'] = user['_id']
                    deposit['amount'] = int(left)
                    deposit['interest_rate'] = bank['default_interest_rate']
                    deposit.save()
                data['amount'] = amount - bank['withdrawal_fee']

            else:
                if user_settings['coins_total'] < (amount + bank['deposit_fee']):
                    amount -= (amount +
                               bank['deposit_fee'] -
                               user_settings['coins_total'])

                deposit = self.db.Deposit()
                deposit['user'] = user['_id']
                deposit['bank'] = bank['_id']
                deposit['amount'] = amount
                deposit['interest_rate'] = bank['default_interest_rate']
                deposit.save()

                user_settings['coins_total'] -= amount
                user_settings['coins_total'] -= bank['deposit_fee']
                user_settings.save()
                data['amount'] = amount + bank['deposit_fee']
        else:
            data['errors'] = errors
        self.write(data)


# this handler gets automatically appended last to all handlers inside app.py
class PageNotFoundHandler(BaseHandler):

    def get(self):
        path = self.request.path
        page = path[1:]
        if page.endswith('/'):
            page = page[:-1]
        page = page.split('/')[-1]
        if page.split(',')[0] in self.PLUGINS:
            ua = self.request.headers.get('User-Agent')
            if ua and MOBILE_USER_AGENTS.search(ua) and not self.get_cookie('no-mobile'):
                path = '/mobile%s' % path
            new_url = '%s#%s' % (
              path.replace(page, '').replace('//', '/'),
              page
            )
            self.redirect(new_url)
            return
        if not path.endswith('/'):
            new_url = '%s/' % path
            if self.request.query:
                new_url += '?%s' % self.request.query
            self.redirect(new_url)
            return
        raise HTTPError(404, path)


@route('/admin/all-images/?')
class AllImagesHandler(BaseHandler, PictureThumbnailMixin):

    LIMIT = 100

    @tornado.web.addslash
    def get(self):
        data = {}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT

        pictures = []
        data['count'] = (
            self.db.QuestionPicture
            .find()
            .count()
        )
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)

        question_pictures = (
            self.db.QuestionPicture
            .find()
            .sort('modify_date', -1)
            .limit(self.LIMIT)
            .skip(skip)
        )
        pictures = []

        picture_count = defaultdict(int)
        for p in self.db.QuestionPicture.collection.find(None, ('question',)):
            picture_count[p['question']] += 1

        for picture in question_pictures:
            if picture_count[picture['question']] == 4:
                max_width, max_height = settings.FOUR_PICTURES_WIDTH_HEIGHT
                sizes = (
                    # when shown in table
                    (settings.FOUR_PICTURES_WIDTH_HEIGHT, {'crop': True}),
                    # when shown in the result
                    ((40, 40), {}),
                )
            else:
                sizes = (
                  (settings.PICTURE_QUESTION_WIDTH_HEIGHT, {}),
                )
            for size, kwargs in sizes:
                # as it appears in a question:
                uri, (width, height) = self.get_thumbnail(
                    picture,
                    size,
                    **kwargs
                )
                url = self.static_url(uri.replace('/static/', ''))
                pictures.append((url, (width, height)))
        data['pictures'] = pictures

        self.render('admin/all-images.html', **data)


## thank you django.core.validators
email_re = re.compile(
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"  # dot-atom
    # quoted-string, see also http://tools.ietf.org/html/rfc2822#section-3.2.5
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|\\[\001-\011\013\014\016-\177])*"'
    r')@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?$)'  # domain
    r'|\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$',
    re.IGNORECASE)  # literal form, ipv4 address (SMTP 4.1.3)


@route('/league.json', name='league')
class League(AuthenticatedBaseHandler, LeagueMixin):

    LINK_SHIM = '<special link inserted here>'

    def get(self):
        data = {}
        if self.get_argument('find', None):
            self.write(self.find_users(self.get_argument('find')))
            return
        if self.get_argument('preview', None):
            self.write({'text': self.get_preview_text()})
            return
        if self.get_argument('about', None):
            self.write({'info': self.get_user_info(self.get_argument('about'))})
            return
        user = self.get_current_user()
        total_earned = self.get_total_earned(user)
        rank = (self.db.TotalEarned
                .find({'coins': {'$gt': total_earned['coins']}})
                .count() + 1)
        data['total_earned'] = {
            'coins': total_earned['coins'],
            'rank': rank
        }
        data['highscore'] = self.get_highscore(user)
        data['invites'] = self.get_pending_invites(user)
        self.write(data)

    def get_user_info(self, user_id):
        info = {}
        user = self._find_user(user_id)
        info['name'] = self.get_name(user)
        user_settings = self.get_user_settings(user)
        current_location = self.get_current_location(user)
        total_earned = self.get_total_earned(user)
        info['cities_visited'] = len(self.db.Flight
                                     .find({'user': user['_id']})
                                     .distinct('to'))
        rank = (self.db.TotalEarned
                .find({'coins': {'$gt': total_earned['coins']}})
                .count() + 1)
        info['global_rank'] = rank
        info['joined'] = smartertimesince(user['add_date'])
        info['miles_total'] = int(round(user_settings['miles_total']))
        info['current_location'] = unicode(current_location)
        info['total_earned'] = dict((k, v) for (k, v)
                                    in total_earned.items()
                                    if isinstance(v, int))
        return info

    def get_preview_text(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        total_earned = self.get_total_earned(user)
        text = self.render_string('invite_text.txt', **{
            'total_earned_coins': total_earned['coins'],
            'current_location': current_location['city'],
            'link_shim': self.LINK_SHIM,
        })
        return text

    def find_users(self, search):
        search1 = re.compile('^%s' % re.escape(search), re.I)
        current_user = self.get_current_user()
        result = []
        _ids = set()
        def append(user):
            if user['_id'] in _ids:
                return
            _ids.add(user['_id'])
            connected = self.db.Friendship.find_one({
                'user': current_user['_id'],
                'to': user['_id']
            })
            if connected:
                return
            result.append([
                str(user['_id']),
                user['username'],
                user['email'],
                ('%s %s' % (user['first_name'], user['last_name'])).strip()
            ])
        select = ('username', 'first_name', 'last_name', 'email')
        # XXX how to OR these?
        for key in ('username', 'email', 'first_name', 'last_name'):
            for each in (self.db.User.collection
                         .find({key: search1}, select)):
                append(each)
        data = {
            'count': len(result),
            'result': result[:10],
            'capped': len(result) > 10,
        }
        return data

    def get_highscore(self, this_user):
        list_ = []

        for i, (total, user_id) in enumerate(self.get_highscore_fast(this_user)):
            user = (self.db.User.collection
                    .find_one({'_id': user_id},
                              ('first_name', 'last_name', 'email', 'username')))
            is_you = user['_id'] == this_user['_id']
            name = self.get_name(user)
            if is_you and this_user['anonymous']:
                name = 'You'
            list_.append({
                'total': self.get_total_earned(user)['coins'],
                'name': name,
                'you': is_you,
                'id': str(user_id),
            })

        list_.sort(key=lambda x: x['total'], reverse=True)
        return list_

    def post(self):
        if (self.get_argument('email', None) and
            self.get_argument('text', None)):
            email = self.get_argument('email')
            text = self.get_argument('text')
            sent, errors = self.send_invite(email, text)
            if errors:
                self.write({'errors': errors})
            else:
                self.write({'sent': sent})
            return
        data = {}
        this_user = self.get_current_user()
        user = self._find_user(self.get_argument('id'))
        assert user
        friendship = self.db.Friendship.find_one({
            'user': this_user['_id'],
            'to': user['_id']
        })
        if friendship:
            self.write({'error': 'ALREADYFRIENDS'})
            return

        friendship = self.db.Friendship()
        friendship['user'] = this_user['_id']
        friendship['to'] = user['_id']
        friendship.save()

        inverse = self.db.Friendship.find_one({
            'user': user['_id'],
            'to': this_user['_id']
        })
        if inverse:
            inverse['mutual'] = True
            inverse.save()
            friendship['mutual'] = True
            friendship.save()

        if friendship['mutual']:
            notified = self.notify_accepted_friendship(
                user,
                this_user,
            )
        else:
            notified = self.notify_new_friendship(
                user,
                this_user,
            )

        data['notified'] = notified

        self.write(data)

    def send_invite(self, email, text):
        sent = None
        errors = []

        if not email_re.match(email):
            errors.append("Error: Email address appears to not be valid.")
        if self.LINK_SHIM not in text:
            errors.append("Error: Special link shim not in text any more.")

        if not errors:
            try:
                sent = self._send_invite(email, text)
            except Exception:
                logging.error('Unable to send invite', exc_info=True)
                sent = False

        return sent, errors

    def _send_invite(self, email, text):
        user = self.get_current_user()
        token = self.db.FriendshipToken()
        token['user'] = user['_id']
        token.generate_token(12)
        token.save()

        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        join_url = base_url + self.reverse_url(
            'join_friendship',
            token['token']
        )
        assert self.LINK_SHIM in text
        text = text.replace(self.LINK_SHIM, join_url)
        body = text  # XXX maybe HTML some day
        subject = "Join my League of Friends on %s" % settings.PROJECT_TITLE
        send_email(
            self.application.settings['email_backend'],
            subject,
            body,
            self.application.settings['admin_emails'][0],
            [email],
            bcc=self.application.settings['admin_emails']
        )
        invitation = self.db.Invitation()
        invitation['user'] = user['_id']
        invitation['email'] = email
        invitation['message'] = text
        invitation.save()

        return True

    def _find_user(self, _id):
        try:
            user = self.db.User.find_one({'_id': ObjectId(_id)})
        except InvalidId:
            raise HTTPError(400, _id)
        if not user:
            raise HTTPError(400, _id)
        return user

    def notify_accepted_friendship(self, *args, **kwargs):
        try:
            return self._notify_accepted_friendship(*args, **kwargs)
        except Exception:
            logging.error(
                'Unable to notify about accepted of friendship',
                exc_info=True
            )
            return False

    def _notify_accepted_friendship(self, user, from_user):
        user_settings = self.get_user_settings(user)
        if user_settings.get('unsubscribe_emails'):
            return False

        users_rankings = {}
        highscores = self.get_highscore_fast(from_user)
        for i, (total, user_id) in enumerate(highscores):
            users_rankings[user_id] = (i + 1, total)

        your_total_earned = self.get_total_earned(user)
        your_rank = users_rankings[user['_id']][0]
        their_total_earned = self.get_total_earned(from_user)
        their_rank = users_rankings[from_user['_id']][0]

        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        league_url = base_url + '/league'
        body = self.render_string('friendship_accepted.txt', **{
            'their_total_earned': their_total_earned,
            'their_rank': their_rank,
            'their_name': self.get_name(from_user),
            'your_name': self.get_name(user),
            'your_total_earned': your_total_earned,
            'your_rank': your_rank,
            'league_url': league_url,
        })
        subject = ("%s on your League of Friends" %
                   (self.get_name(from_user),)
                   )
        send_email(
            self.application.settings['email_backend'],
            subject,
            body,
            self.application.settings['admin_emails'][0],
            [user['email']],
        )
        return True

    def notify_new_friendship(self, *args, **kwargs):
        try:
            return self._notify_new_friendship(*args, **kwargs)
        except Exception:
            logging.error('Unable to notify of friendship', exc_info=True)
            return False

    def _notify_new_friendship(self, user, from_user):
        user_settings = self.get_user_settings(user)
        if user_settings.get('unsubscribe_emails'):
            return False

        users_rankings = {}
        highscores = self.get_highscore_fast(from_user)
        for i, (total, user_id) in enumerate(highscores):
            users_rankings[user_id] = (i + 1, total)

        your_total_earned = self.get_total_earned(user)
        your_rank = users_rankings[user['_id']][0]
        their_total_earned = self.get_total_earned(from_user)
        their_rank = users_rankings[from_user['_id']][0]
        token = self.db.FriendshipToken()
        token['user'] = from_user['_id']
        token['to'] = user['_id']
        token.generate_token(12)
        token.save()

        base_url = '%s://%s' % (self.request.protocol, self.request.host)
        accept_url = base_url + self.reverse_url(
            'accept_friendship',
            token['token']
        )
        body = self.render_string('friendship_created.txt', **{
            'their_total_earned': their_total_earned,
            'their_rank': their_rank,
            'their_name': self.get_name(from_user),
            'your_name': self.get_name(user),
            'your_total_earned': your_total_earned,
            'your_rank': your_rank,
            'accept_url': accept_url,
        })

        subject = ("You've been added to %s's League of Friends" %
                   (self.get_name(from_user),)
                   )

        send_email(
            self.application.settings['email_backend'],
            subject,
            body,
            self.application.settings['admin_emails'][0],
            [user['email']],
        )
        return True


@route('/accept/(\w{12})', name='accept_friendship')
class AcceptFriendshipHandler(BaseHandler):

    def get(self, token):
        friendship_token = self.db.FriendshipToken.find_one({'token': token})
        if not friendship_token:
            self.redirect('/league')
            return
            #raise HTTPError(404, 'Invalid token')
        user = self.db.User.find_one({'_id': friendship_token['user']})
        to = self.db.User.find_one({'_id': friendship_token['to']})

        friendship = self.db.Friendship.find_one({
            'user': user['_id'],
            'to': to['_id'],
        })
        friendship['mutual'] = True
        friendship.save()

        new_friendship = self.db.Friendship()
        new_friendship['user'] = to['_id']
        new_friendship['to'] = user['_id']
        new_friendship['mutual'] = True
        new_friendship.save()

        friendship_token.delete()

        self.redirect('/league')


@route('/join/(\w{12})', name='join_friendship')
class JoinFriendshipHandler(BaseHandler):

    def get(self, token):
        friendship_token = self.db.FriendshipToken.find_one({'token': token})
        if not friendship_token:
            self.redirect('/league')
            return
            #raise HTTPError(404, 'Invalid token')
        invites = self.get_secure_cookie('invites')
        if invites is None:
            invites = []
        else:
            invites = invites.split('|')
        invites.append(friendship_token['token'])
        self.set_secure_cookie('invites', '|'.join(invites))

        self.redirect('/')


@route('/unsubscribe/(\w{12})', name='unsubscribe')
class UnsubscribeHandler(BaseHandler):

    def get(self, token):
        for user in (self.db.User.collection
                     .find({'email': {'$ne': None}}, ('_id',))):
            if self.db.User.tokenize_id(user['_id'], 12) == token:
                user = self.db.User.find_one({'_id': user['_id']})
                break

        user_settings = self.get_user_settings(user)
        user_settings['unsubscribe_emails'] = True
        user_settings.save()

        self.redirect('/unsubscribed')


@route('/news.json', name='news')
class NewsHandler(BaseHandler):

    def get(self):
        data = {}
        user = self.get_current_user()

        def describe_newsitem(item):
            body = markdown.markdown(
                item['body']
            )

            info = {
                'title': item['title'],
                'body': item['body'],
                'body_html': body,
                'id': str(item['_id']),
                'read': item['read'],
                'age': smartertimesince(
                    item['add_date'],
                    datetime.datetime.utcnow()
                )
            }
            return info

        if self.get_argument('id', None):
            item = self._get_newsitem(user, self.get_argument('id'))
            if not item:
                self.write({'error': 'INVALIDNEWSITEMS'})
                return
            was_unread = not item['read']
            if was_unread:
                item['read'] = True
                item.save()
            info = describe_newsitem(item)
            data['newsitem'] = info
        else:
            items = []
            for each in (self.db.NewsItem.collection
                         .find({'user': user['_id']})
                         .sort('add_date', -1)):
                items.append(describe_newsitem(each))
            data['newsitems'] = items

        self.write(data)

    def _get_newsitem(self, user, _id):
        try:
            item = self.db.NewsItem.find_one({'_id': ObjectId(_id)})
            assert item
            return item
        except:
            logging.error('Unable to find news item %r' % _id, exc_info=True)
