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

    def get_current_location(self, user=None):
        if user is None:
            user = self.get_current_user()
        if user:
            if user['current_location']:
                return (self.db.Location
                        .find_one({'_id': user['current_location']}))

    @property
    def redis(self):
        return self.application.redis

    @property
    def db(self):
        return self.application.db


    def render(self, template, **options):
        if not options.get('page_title'):
            options['page_title'] = settings.PROJECT_TITLE

        options['user_name'] = 'Peter Bengtsson'
        options['user_miles_total'] = '12,345'
        options['user_coins_total'] = 325

        options['javascript_test_file'] = self.get_argument('test', None)

        return tornado.web.RequestHandler.render(self, template, **options)

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


@route('/')
class HomeHandler(BaseHandler):

    def get(self):
        options = {}

        self.render('home.html', **options)

@route('/offline/')
class OfflineHomeHandler(HomeHandler):

    def get(self):
        options = {}
        options['javascript_test_file'] = self.get_argument('test', None)
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

    #def check_xsrf_cookie(self):
    #    pass

    def get(self):
        user = self.get_current_user()
        location = self.get_current_location(user)
        data = {}
        data['quiz_name'] = 'Mathematics Professor!'
        question = self._get_next_question(user, location)
        if not question['alternatives_sorted']:
            random.shuffle(question['alternatives'])
        data['question'] = question
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

Questions = (
  {
  'text': 'What is 1 + 1?',
  'id': 'abc1234',
  'alternatives': ['1', '2', '3', '4'],
  'correct': '2',
  },
  {
  'text': 'Who makes the web browser Firefox?',
  'id': 'abc555',
  'alternatives': ['Microsoft', 'Google', 'Apple', 'Mozilla'],
  'correct': 'Mozilla',
  },
  {
  'text': 'What main language to they speak in Sweden',
  'id': 'abc444',
  'alternatives': ['Danish', 'Finnish', 'Norveigen', 'Swedish'],
  'correct': 'Swedish',
  },
)


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
