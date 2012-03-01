import re
import datetime
import random
import os
import logging
import traceback
from collections import defaultdict
from cStringIO import StringIO
from pprint import pprint
import tornado.auth
import tornado.web
import tornado.gen
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


ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7
FULL_DATE_FMT = '%d %b %Y'


def calculate_distance(from_location, to_location):
    from_ = (from_location['lat'], from_location['lng'])
    to = (to_location['lat'], to_location['lng'])
    return geopy_distance(from_, to)


class NoQuestionsError(RuntimeError):
    pass


class NoLocationsError(RuntimeError):
    pass


class BaseHandler(tornado.web.RequestHandler):

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
            state['user']['name'] = user.get_full_name()
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

    def static_url(self, path):
        if self.application.settings['embed_static_url_timestamp']:
            ui_module = self.application.ui_modules['StaticURL'](self)
            try:
                return ui_module.render(path)
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


class AuthenticatedBaseHandler(BaseHandler):

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.write_json({'error': 'NOTLOGGEDIN'})
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


@route('/quizzing.json$', name='quizzing')
class QuizzingHandler(AuthenticatedBaseHandler, PictureThumbnailMixin):

    # number between 0 and (inclusive) 1.0 that decides how many coins to
    # give for a percentage.
    PERCENTAGE_COINS_RATIO = 1.0

    SECONDS = 10
    NO_QUESTIONS = settings.QUIZ_MIN_NO_QUESTIONS

    def points_to_coins(self, points):
        max_ = self.NO_QUESTIONS * Question.HIGHEST_POINTS_VALUE
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
            session.save()

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

        try:
            question = self._get_next_question(
              session,
              category,
              location,
              previous_question=previous_question
            )
        except NoQuestionsError:
            self.write_json({'error': 'NOQUESTIONS'})
            return
        if not question['alternatives_sorted']:
            random.shuffle(question['alternatives'])

        answer = self.db.SessionAnswer()
        answer['question'] = question['_id']
        answer['session'] = session['_id']
        answer.save()

        _no_answers = (self.db.SessionAnswer
                       .find({'session': session['_id']})
                       .count())
        data['no_questions'] = {
          'total': self.NO_QUESTIONS,
          'number': _no_answers,
          'last': _no_answers == self.NO_QUESTIONS,
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
        data['question']['seconds'] = self.SECONDS
        self.write_json(data)

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
            self.write_json({'ok': True})
            return

        session, = (self.db.QuestionSession
                    .find({'user': user['_id'],
                           'location': location['_id'],
                           'finish_date': None})
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
            summary = []
            for answer in (self.db.SessionAnswer
                           .find({'session': session['_id']})
                           .sort('add_date', 1)  # oldest first
                           ):
                if answer['timedout'] and answer['points'] is None:
                    raise Exception("this shouldn't happen any more")
                    answer['points'] = 0
                    answer.save()
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

            data['results'] = {
              'total_points': total_points,
              'coins': coins,
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
            data['points_value'] = question.get('points_value', 1)
            assert isinstance(data['points_value'], int)

            answer_obj['time'] = time_
            answer_obj['answer'] = answer
            answer_obj['correct'] = data['correct']
            answer_obj['points'] = data['points_value'] * data['correct']
            answer_obj['timedout'] = False
            answer_obj.save()

        self.write_json(data)


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
        for location in (self.db.Location
                         .find({'airport_name': {'$ne': None}})):
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
                               (from_, to, _commafy(int(flight['miles']))))
                type_ = 'flight'
            else:
                raise NotImplementedError
            transaction['description'] = description
            transaction['type'] = type_
            transactions.append(transaction)
        return transactions, count

    def post(self):
        # XXX this is just a temporary hack
        if self.get_argument('cheat'):
            user = self.get_current_user()
            location = self.get_current_location()
            category = self.db.Category.find_one({'name': 'Cheater'})
            if not category:
                category = self.db.Category()
                category['name'] = u'Cheater'
                category.save()
            if self.db.Job.find({'user': user['_id'],
                                     'location': location['_id'],
                                     'category': category['_id']}).count():

                self.write_json({'ERROR': 'Cheated here already'})
                return
            else:
                COINS = 1000
                job = self.db.Job()
                job['user'] = user['_id']
                job['coins'] = COINS
                job['category'] = category['_id']
                job['location'] = location['_id']
                job.save()

                user_settings = self.get_current_user_settings()
                user_settings['coins_total'] += COINS
                user_settings.save()
                self.write_json({'coins': COINS})
                return
        self.write_json({'ERROR': 'Wrong code'})


def _commafy(s):
    r = []
    for i, c in enumerate(reversed(str(s))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)


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
                         .find({'airport_name': {'$ne': None}})
                         .sort('city', 1)):
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
            data['count_pictures']=0#data['count_pictures'] = self.get_pictures_count(location)
            data['count_messages'] = self.get_messages_count(location)

        self.write(data)

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
              'time_ago': smartertimesince(item['add_date']),
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
        for q in (self.db.Question
                  .find({'location': location['_id'],
                         'published': True})):
            category = _categories[q['category']]
            categories[category['name']] += 1
            point_values[category['name']] += q['points_value']
        jobs = []
        for category in _categories.values():
            no_questions = categories[category['name']]
            if no_questions < QuizzingHandler.NO_QUESTIONS:
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

        jobs.sort(lambda x, y: cmp(x['description'], y['description']))
        return jobs

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
        return {'messages': self.get_messages(location, limit=1)}


@route('/pinpoint.json$', name='pinpoint')
class PinpointHandler(AuthenticatedBaseHandler):

    # number between 0 and (inclusive) 1.0 that decides how many coins to
    # give for a percentage.
    PERCENTAGE_COINS_RATIO = 1.0

    MIN_DISTANCE = 50.0
    NO_QUESTIONS = 10
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

    BASE_PRICE = 100  # coins

    def get(self):
        user = self.get_current_user()
        current_location = self.get_current_location(user)
        data = {
          'airport_name': current_location['airport_name'],
        }
        destinations = []
        for location in (self.db.Location
                          .find({'_id': {'$ne': current_location['_id']},
                                 'airport_name': {'$ne': None}})):
            if not self.enough_questions(location):
                continue
            distance = calculate_distance(current_location, location)
            cost = self.calculate_cost(distance.miles, user)
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
        return self.BASE_PRICE + int(round(miles * .1))

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



@route('/fly.json$', name='fly')
class FlyHandler(AirportHandler):

    def get(self):
        user = self.get_current_user()
        route = self.get_argument('route')
        from_, to = re.findall('[A-Z]{3}', route)
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
        subject = "New user!"
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

    def post_login_successful(self, user):
        """executed by the Google, Twitter and Facebook
        authentication handlers"""
        try:
            self._post_login_successful(user)
        except:  # pragma: no cover
            logging.error("Failed to post login successful user",
                          exc_info=True)

    def _post_login_successful(self, user):
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
            import uuid
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

        self.post_login_successful(user)
        self.set_secure_cookie("user", str(user._id), expires_days=100)
        self.redirect(self.get_next_url())


@route(r'/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def post(self):
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
