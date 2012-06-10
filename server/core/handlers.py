import uuid
import re
import datetime
import random
import os
import logging
import traceback
import mimetypes
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
from pymongo.objectid import InvalidId, ObjectId
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

    #def write(self, *a, **k):
    #    from time import sleep
    #    sleep(1.2)
    #    super(BaseHandler, self).write(*a, **k)

    def write_json(self, struct, javascript=False):
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
        E.g. if filename is '/static/image.png' and you return '//cloudfront.com'
        then final URL presented in the template becomes
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


class AuthenticatedBaseHandler(BaseHandler):

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.write({'error': 'NOTLOGGEDIN'})
            self.finish()


@route('/')
class HomeHandler(BaseHandler):

    def render(self, template, **options):
        options['javascript_test_file'] = self.get_argument('test', None)
        options['state'] = self.get_state()
        #options['state_json'] = tornado.escape.json_encode(self.get_state())
        return super(HomeHandler, self).render(template, **options)

    def get(self):
        options = {}
        ua = self.request.headers.get('User-Agent')
        if ua and MOBILE_USER_AGENTS.search(ua) and not self.get_cookie('no-mobile'):
            self.redirect('/mobile/')
            return
        self.render('home.html', **options)


@route('/offline/')
class OfflineHomeHandler(HomeHandler):

    def get(self):
        options = {}
        self.render('offline.html', **options)

@route('/mobile/')
class MobileHomeHandler(HomeHandler):

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
        self.write_json(data)

    def post(self):
        print repr(self.request.body)
        data = tornado.escape.json_decode(self.request.body)
        print data
        self.write_json({'status': 'OK'})


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
        #print repr(tornado.escape.linkify(text))
        text = markdown.markdown(
          tornado.escape.linkify(text, extra_params='target="_blank"')
        )
        #print repr(text)
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
            for picture in (self.db.QuestionPicture
                            .find({'question': {'$in': session['questions']}})
                            ):
                uri, (width, height) = self.make_thumbnail(picture, (250, 250))
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
                previous_question['points'] = 0
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
            no_questions = (self.db.Question
                            .find({'category': category['_id']})
                            .count())
        data['no_questions'] = {
          'total': no_questions,
          'number': _no_answers,
          'last': _no_answers == no_questions,
        }

        data['question'] = {
          'text': question['text'],
          'alternatives': question['alternatives'],
        }
        if question.has_picture():
            picture = question.get_picture()
            uri, (width, height) = self.make_thumbnail(picture, (250, 250))

            url = self.static_url(uri.replace('/static/', ''))
            data['question']['picture'] = {
              'url': url,
              'width': width,
              'height': height,
            }
        data['question']['seconds'] = question['seconds']
        self.write_json(data)

    def _pick_questions(self, user, location, category, allow_repeats=False):
        filter_ = {
          'location': location['_id'],
          'category': category['_id']
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
                answer_obj['points'] = 0
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
                summary.append({
                  'question': question['text'],
                  'correct_answer': question['correct'],
                  'your_answer': answer['answer'],
                  'correct': answer['correct'],
                  'time': (not answer['timedout']
                           and answer['time']
                           or None),
                  'points': answer['points'],
                  'timedout': answer['timedout'],
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
            job['location'] = session['location']
            job.save()

            print "RIGHTS", rights
            data['results'] = {
              'total_points': total_points,
              'coins': coins,
              'percentage_right': 100.0 * sum(rights) / len(rights)
            }

        else:
            question = (self.db.Question
                        .find_one({'_id': answer_obj['question']}))

            if question.get('didyouknow'):
                data['didyouknow'] = self.render_didyouknow(question['didyouknow'])

            answer = self.get_argument('answer')
            time_ = float(self.get_argument('time'))
            data['correct'] = question.check_answer(answer)
            if not data['correct']:
                data['correct_answer'] = question['correct']

            time_left = question['seconds'] - time_
            time_bonus_p = round(float(time_left) / question['seconds'], 1)
            data['time_bonus'] = 1 + time_bonus_p
            data['points_value'] = question.get('points_value', 1)
            data['points'] = data['time_bonus'] * data['points_value'] * data['correct']
            #data['points'] = float('%.1f' % data['points'])
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
                earning['coins'] = QuestionWriterHandler.COINS_EARNING_VALUE
                earning.save()

        self.write_json(data)

@route('/questionrating.json$', name='question_rating')
class QuestionRatingHandler(AuthenticatedBaseHandler):

    def post(self):
        score = int(self.get_argument('score'))
        #print "SCORE", repr(score)
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
        user_settings = self.get_user_settings(user)
        assert user_settings
        data = {}
        data['disable_sound'] = user_settings['disable_sound']
        self.write_json(data)

    def post(self):
        user = self.get_current_user()
        user_settings = self.get_user_settings(user)
        disable_sound = bool(self.get_argument('disable_sound', False))
        user_settings['disable_sound'] = disable_sound
        user_settings.save()
        self.get()


@route('/miles.json$', name='miles')
class MilesHandler(AuthenticatedBaseHandler):

    def get(self):
        user = self.get_current_user()
        data = {}
        _cities = set()
        for each in self.db.Flight.collection.find({'user': user['_id']}):
            _cities.add(each['from'])
            _cities.add(each['to'])
        data['no_cities'] = max(1, len(_cities))
        data['flights'] = self.get_flights(user)
        data['percentage'] = 0
        self.write_json(data)

    def get_flights(self, user):
        flights = []
        filter_ = {'user': user['_id']}
        _locations = {}
        for location in self.db.Location.find():
            _locations[location['_id']] = location.dictify()

        for each in (self.db.Flight
                     .find(filter_)
                     .sort('add_date', 1)):  # oldest first
            flight = {
              'from': _locations[each['from']],
              'to': _locations[each['to']],
              'miles': int(each['miles']),
              'date': each['add_date'].strftime(FULL_DATE_FMT),
            }
            flights.append(flight)
        return flights


@route('/coins.json$', name='coins')
class CoinsHandler(AuthenticatedBaseHandler):

    def get(self):
        user = self.get_current_user()
        data = {}
        if self.get_argument('transactions-page', None) is not None:
            data['transactions'], count = self.get_transactions(user)
            data['count_transactions'] = count
        if self.get_argument('jobs-page', None) is not None:
            data['jobs'], count = self.get_jobs(user)
            data['count_jobs'] = count
        self.write_json(data)

    def get_jobs(self, user, limit=10):
        jobs = []
        filter_ = {'user': user['_id']}
        records = self.db.Job.find(filter_)
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
        records = self.db.Transaction.find(filter_)
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
class CityHandler(AuthenticatedBaseHandler, PictureThumbnailMixin):

    FLAGS = {
      'Sweden': 'sweden.png',
    }

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

    def get_flag(self, location):
        country = location['country']
        if country not in self.FLAGS:
            logging.warn("No flag for %r" % country)
            return
        return self.static_url(os.path.join('images/flags',
                                            self.FLAGS[country]))

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
            data['count_pictures'] = self.get_pictures_count(location)
            data['count_messages'] = self.get_messages_count(location)

            data['has_introduction'] = bool(self.get_intro_html(location))
            data['has_ambassadors'] = bool(self.get_ambassadors_html(location))
            data['state'] = self.get_state()

        self.write(data)

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


    def get_pictures_count(self, location):
        search = {'location': location['_id'], 'published': True}
        return self.db.LocationPicture.find(search).count()

    def get_pictures(self, location):
        pictures = []
        search = {'location': location['_id'], 'published': True}
        for item in (self.db.LocationPicture
                     .find(search)
                     .sort('index')):
            uri, (width, height) = self.make_thumbnail(item, (700, 700))  # XXX might need some more thought
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

        nomansland = self.db.Location.find_one({'city': self.NOMANSLAND['city']})
        if nomansland:
            if not self.db.Question.find({'location': nomansland['_id']}).count():
                # we need to create the tutorial questions
                self.create_tutorial_questions(nomansland)

        for q in (self.db.Question
                  .find({'location': location['_id'],
                         'published': True})):
            category = _categories[q['category']]
            categories[category['name']] += 1
            point_values[category['name']] += q['points_value']

        jobs = []
        for category in _categories.values():
            no_questions = categories[category['name']]
            if location == nomansland:
                # you're in Nomansland
                if category['name'] != 'Tutorial':
                    continue
            elif no_questions < QuizzingHandler.NO_QUESTIONS:
                continue

            job = {
              'type': 'quizzing',
              'category': category['name'],
              'description': ('%s (%s questions)' %
                              (category['name'], no_questions)),
            }
            jobs.append(job)

        _center_search = {'country': location['country'],
                          'locality': location['locality']}
        _center = self.db.PinpointCenter.find_one(_center_search)
        if not _center:
            _center_search = {'country': location['country']}
            _center = self.db.PinpointCenter.find_one(_center_search)
        if _center:
            _cities = self.db.Location.find(_center_search)
            if _cities.count() > PinpointHandler.NO_QUESTIONS:
                description = 'Geographer (%d cities)' % _cities.count()
                jobs.append({
                  'type': 'pinpoint',
                  'description': description,
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
            uri, (width, height) = self.make_thumbnail(item, (300, 300))
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
            for answer in self.db.SessionAnswer.find({'session': other_session['_id']}):
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
                coins = self.points_to_coins(points, seconds_total, points_value)
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

        # if the last job was of the same category and location
        # then increment the number of coins
        for job in (self.db.Job.find({'user': user['_id'],
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

        data['left'] = self._count_questions_left(category, user, current_location)

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

    # number between 0 and (inclusive) 1.0 that decides how many coins to
    # give for a percentage.
    PERCENTAGE_COINS_RATIO = 1.0

    MIN_DISTANCE = 50.0
    NO_QUESTIONS = settings.PINPOINT_NO_QUESTIONS
    SECONDS = 100

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
                self.write_json({'error': 'NOLOCATIONS'})
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
                self.write_json({'error': 'ALREADYSENTALLLOCATIONS'})
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

        self.write_json(data)

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

        self.write_json(data)


@route('/airport.json$', name='airport')
class AirportHandler(AuthenticatedBaseHandler):

    BASE_PRICE = 20  # coins

    def get(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        data = {
          'airport_name': current_location['airport_name'],
        }
        only_affordable = self.get_argument('only_affordable', False)

        destinations = []
        for location in (self.db.Location
                          .find({'_id': {'$ne': current_location['_id']},
                                 'available': True})):
            if not self.enough_questions(location):
                continue
            distance = calculate_distance(current_location, location)
            cost = self.calculate_cost(distance.miles, user)
            if only_affordable:
                user_settings = self.get_current_user_settings(user)
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
              'miles': distance.miles,
            }
            destinations.append(destination)

        if not only_affordable:
            destinations.append({
              'id': 'moon',
              'code': '',
              'city': '',
              'country': '',
              'locality': 'space',
              'name': 'Moon',
              'cost': 1000000,
              'miles': 238857,
            })
        data['destinations'] = destinations
        self.write_json(data)

    def calculate_cost(self, miles, user):
        return self.BASE_PRICE + int(round(miles * .05))


@route('/fly.json$', name='fly')
class FlyHandler(AirportHandler):

    def get(self):
        user = self.get_current_user()
        route = self.get_argument('route')
        # use [0-9] only for the Nomansland thing
        from_, to = re.findall('[0-9A-Z]{3}', route)
        from_ = self.db.Location.find_one({'code': from_})
        if not from_:
            self.write_json({'error': 'INVALIDAIRPORT'})
            return
        to = self.db.Location.find_one({'code': to})
        if not to:
            self.write_json({'error': 'INVALIDAIRPORT'})
            return
        if from_ == to:
            self.write_json({'error': 'INVALIDROUTE'})
            return
        flight = self.db.Flight.find_one({
          'user': user['_id'],
          'from': from_['_id'],
          'to': to['_id'],
        })
        if not flight:
            self.write_json({'error': 'INVALIDROUTE'})
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
        print "FINAL"
        pprint(data)
        self.write_json(data)

    def post(self):
        _id = self.get_argument('id')
        location = self.db.Location.find_one({'_id': ObjectId(_id)})
        assert location
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        assert location != current_location
        distance = calculate_distance(current_location, location)
        cost = self.calculate_cost(distance.miles, user)
        state = self.get_state()
        if cost > state['user']['coins_total']:
            self.write_json({'error': 'CANTAFFORD'})
            return

        # make the transaction
        user_settings = self.get_current_user_settings(user)
        user_settings['coins_total'] -= cost
        user_settings['miles_total'] += distance.miles
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

        data = {
          'from_code': current_location['code'],
          'to_code': location['code'],
          'cost': cost,
        }
        self.write_json(data)


@route('/state.json$', name='state')
class StateHandler(BaseHandler):

    def get(self):
        state = self.get_state()
        #if format == 'html':
        #    self.render('div.usernav.html', state=state)
        #else:
        self.write_json({'state': state})


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

            if previous_user and previous_user['anonymous'] and not user['anonymous']:
                self._transferUser(previous_user, user)

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
        )

        for each in models:
            if isinstance(each, tuple):
                model, key = each
            else:
                model, key = each, 'user'

            for each in model.find({key: old['_id']}):
                each[key] = new['_id']
                each.save()

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
                   (user['username'], settings.PROJECT_TITLE))
        body = []
        if inviter['first_name']:
            body.append('Hi %s' % inviter['first_name'])
        else:
            body.append('Hi %s' % inviter['username'])
        body.append('')
        body.append("Your invitation sent to %s did work out!" % invitation['email'])
        if user['first_name']:
            name = '%s %s' % (user['first_name'], user['last_name'])
        else:
            name = user['username']
        body.append("Welcome %s to %s!" % (name, settings.PROJECT_TITLE))
        body.append('')
        body.append("For this recruitment you were awarded %s coins. Congratulations!" %
                    self.INVITATION_AWARD)
        inviter_settings = self.get_user_settings(inviter)
        body.append("Your total coins is now: %s coins." % inviter_settings['coins_total'])
        body.append('')
        body.append('--')
        full_url = '%s://%s' % (self.request.protocol, self.request.host)
        body.append(full_url)
        body = '\n'.join(body)
        send_email(
          self.application.settings['email_backend'],
          subject,
          body,
          from_,
          [to]
        )


@route('/auth/anonymous/', name='auth_anonymous')
class AnonymousAuthHandler(BaseAuthHandler):

    def get(self):
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

        user_struct = user
        #locale = user.get('locale')  # not sure what to do with this yet
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
        self.set_secure_cookie("user", str(user._id), expires_days=100)
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
            self.write_json({})
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
        self.write_json(data)
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
        for transaction in self.db.Transaction.find(user_search):
            spent_total += transaction['cost']
            if transaction['flight']:
                spent_flights += transaction['cost']
        data['spent_total'] = spent_total
        data['spent_flights'] = spent_flights

        earned_jobs = 0
        for job in self.db.Job.find(user_search, ('coins',)):
            earned_jobs += job['coins']

        earned_questions = 0
        for earning in (self.db.QuestionAnswerEarning
                        .find(user_search, ('coins',))):
            earned_questions += earning['coins']

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
        for flight in self.db.Flight.find(user_search):
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

        sessions = 0
        answers = 0
        answers_right = 0
        _answered_questions = set()
        for session in (self.db.QuestionSession
                        .find(dict(user_search, finish_date={'$ne': None}),
                              ('_id',))):
            sessions += 1
            for answer in (self.db.SessionAnswer
                           .find({'session': session['_id']},
                                 ('correct', 'question'))):
                answers += 1
                if answer['correct']:
                    answers_right += 1
                _answered_questions.add(answer['question'])

        data['question_sessions'] = sessions
        data['question_answers'] = answers
        data['question_answers_right'] = answers_right
        data['question_answered_unique_questions'] = len(_answered_questions)

        return data


@route('/feedback.json$', name='feedback')
class FeedbackHandler(AuthenticatedBaseHandler):

    def post(self):
        what = self.get_argument('what')
        comment = self.get_argument('comment')
        user = self.get_current_user()
        location = self.get_current_location()

        feedback = self.db.Feedback()
        feedback['what'] = what
        feedback['comment'] = comment
        if user:
            feedback['user'] = user['_id']
            feedback['location'] = location['_id']
        feedback.save()

        self.write_json({'ok': True})

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
                data['points_value'] = '%s (easy)' % data['points_value'];
            elif data['points_value'] == 3:
                data['points_value'] = '%s (medium)' % data['points_value'];
            elif data['points_value'] == 5:
                data['points_value'] = '%s (hard)' % data['points_value'];
            category, = self.db.Category.find({'_id': question['category']})
            data['category'] = category['name']
            data['didyouknow'] = question['didyouknow']
            _ratings = self._get_rating_total(question)
            if _ratings['count']['all']:  # any?
                data['ratings'] = {'average': _ratings['average'],
                                   'count': _ratings['count']}

            if question.has_picture():
                picture = question.get_picture()
                uri, (width, height) = self.make_thumbnail(picture, (250, 250))

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
        data['filepicker_key'] = 'KqEkAS7kSbWDbB_lUozq'
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

        didyouknow = self.get_argument('didyouknow', '').strip()
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
            self._notify_about_new_question(question, current_user, current_location)
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
            send_email(self.application.settings['email_backend'],
                   subject,
                   body,
                   self.application.settings['admin_emails'][0],
                   self.application.settings['admin_emails'],
                   )
        except:
            logging.error("Failed to send email",
                          exc_info=True)


@route('/questionwriter-check.json', name='questionwriter_check')
class QuestionFileURLCheckHandler(AuthenticatedBaseHandler, PictureThumbnailMixin):


    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        file_url = self.get_argument('check_file_url')
        http_client = tornado.httpclient.AsyncHTTPClient()
        response = yield tornado.gen.Task(http_client.fetch, file_url)
        if response.code == 200:
            effective_url = response.effective_url
            ext = effective_url.split('.')[-1]
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
                    #uri, (width, height) = self.make_thumbnail(picture, (250, 250))
                    static_path = self.static_url(new_file_path
                      .replace(self.application.settings['static_path'] + '/', ''))
                    print "FINALLY", static_path
                    self.write({'url': new_file_path, 'static_url': static_path})
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
