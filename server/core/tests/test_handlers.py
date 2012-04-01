import random
import datetime
import os
import json
from pprint import pprint
from urllib import urlencode
import tornado.escape
from pymongo.objectid import ObjectId
from .base import BaseHTTPTestCase
import settings
import tornado_utils.send_mail as mail
from core.handlers import (PinpointHandler, GoogleAuthHandler, QuizzingHandler,
                           CityHandler)


class HandlersTestCase(BaseHTTPTestCase):

    def setUp(self):
        super(HandlersTestCase, self).setUp()
        #TwitterAuthHandler.authenticate_redirect = \
        #  twitter_authenticate_redirect

        newyork = self.db.Location()
        newyork['code'] = u'JFK'
        newyork['airport_name'] = u'John F. Kennedy International Airport'
        newyork['city'] = u'New York City'
        newyork['country'] = u'United States'
        newyork['locality'] = u'New York'
        newyork['lat'] = 1.0
        newyork['lng'] = -1.0
        newyork.save()
        self.newyork = newyork

        tour_guide = self.db.Category()
        tour_guide['name'] = u'Tour guide'
        tour_guide.save()
        self.tour_guide = tour_guide

    def _login(self, username=u'peterbe', email=u'mail@peterbe.com',
               client=None, location=None,
               first_name=u'Peter', last_name=u'Bengtsson'):

        if client is None:
            client = self.client

        def make_google_get_authenticated_user(data):
            def callback(self, func, **__):
                return func(data)
            return callback

        GoogleAuthHandler.get_authenticated_user = \
          make_google_get_authenticated_user({
            'username': username,
            'email': email,
            'first_name': first_name,
            'last_name': u'Bengtsson',
          })
        url = self.reverse_url('auth_google')
        response = client.get(url, {'openid.mode':'xxx'})
        self.assertEqual(response.code, 302)

        user = self.db.User.find_one(dict(username=username))
        assert user

        if location:
            if not isinstance(location, ObjectId):
                location = location['_id']

            user['current_location'] = location
            user.save()
        user_settings = self.db.UserSettings.find_one({'user': user['_id']})

        return user

        #if client is None:
        #    client = self.client
        if not user:
            data = dict(username=username,
                        email=email,
                        first_name="Peter",
                        last_name="Bengtsson")
            user = self.db.User()
            user['username'] = unicode(username)
            user['email'] = unicode(email)
            user['first_name'] = u"Peter"
            user['last_name'] = u"Bengtsson"
            if location:
                if not isinstance(location, ObjectId):
                    location = location['_id']
                user['current_location'] = location
            user.save()

        client.cookies['user'] = \
          self.create_signed_value('user', str(user._id))
        return user

    def _create_question(self, category, location):
        q = self.db.Question()
        q['text'] = (u'(%s) What number question is this?' %
                     (self.db.Question.find().count() + 1,))
        q['correct'] = u'one'
        q['alternatives'] = [u'one', u'two', u'three']
        if not isinstance(category, ObjectId):
            category = category['_id']
        q['category'] = category
        if not isinstance(location, ObjectId):
            location = location['_id']
        q['location'] = location
        q['seconds'] = 10
        q.save()
        return q

    def get_struct(self, url, *args, **kwargs):
        r = self.client.get(url, *args, **kwargs)
        assert r.code == 200, r.code
        assert r.headers['Content-Type'] == 'application/json; charset=UTF-8'
        return tornado.escape.json_decode(r.body)

    def post_struct(self, url, data,  **kwargs):
        r = self.client.post(url, data, **kwargs)
        assert r.code == 200, r.code
        assert r.headers['Content-Type'] == 'application/json; charset=UTF-8'
        return tornado.escape.json_decode(r.body)

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        body = response.body
        if isinstance(body, str):
            body = unicode(body, 'utf-8')
        self.assertTrue(settings.PROJECT_TITLE in body)

    def test_quizzing(self):
        assert not self.db.QuestionSession.find().count()
        url = self.reverse_url('quizzing')

        def _get():
            return self.get_struct(url, {'category': self.tour_guide['name']})

        r = _get()
        self.assertEqual(r, {'error': 'NOTLOGGEDIN'})
        user = self._login(location=self.newyork)

        r = _get()
        self.assertEqual(r, {'error': 'NOQUESTIONS'})

        hongkong = self.db.Location()
        hongkong['city'] = u'Hong Kong'
        hongkong['country'] = u'China'
        hongkong['lat'] = 100.0
        hongkong['lng'] = -100.0
        hongkong.save()
        self._create_question(self.tour_guide, hongkong)

        chef = self.db.Category()
        chef['name'] = u'Chef'
        chef.save()
        self._create_question(chef, self.newyork)

        q = _get()
        self.assertEqual(q, {'error': 'NOQUESTIONS'})

        q1 = self._create_question(self.tour_guide, self.newyork)
        q2 = self._create_question(self.tour_guide, self.newyork)
        r = _get()
        assert r['question']
        assert r['no_questions']
        q = r['question']

        self.assertTrue(q['text'] in (q1['text'], q2['text']))
        qs, = self.db.QuestionSession.find()  # assert there is only 1
        self.assertEqual(qs['user'], user['_id'])
        self.assertEqual(qs['location'], self.newyork['_id'])
        self.assertEqual(r['no_questions']['total'], QuizzingHandler.NO_QUESTIONS)
        self.assertEqual(r['no_questions']['number'], 1)
        self.assertTrue(not r['no_questions']['last'])

        session, = self.db.QuestionSession.find()
        self.assertEqual(session['category'], self.tour_guide['_id'])
        self.assertEqual(session['user'], user['_id'])
        self.assertEqual(session['location'], self.newyork['_id'])
        self.assertTrue(not session['finish_date'])

        sa, = self.db.SessionAnswer.find()
        self.assertEqual(sa['session'], qs['_id'])
        self.assertTrue(sa['question'] in (q1['_id'], q2['_id']))
        self.assertEqual(sa['answer'], None)
        self.assertEqual(sa['correct'], None)
        self.assertEqual(sa['time'], None)
        self.assertEqual(sa['timedout'], None)

        first_q = q
        r = _get()
        second_q = r['question']
        self.assertTrue(first_q != second_q)
        self.assertEqual(r['no_questions']['number'], 2)

        sa1, = self.db.SessionAnswer.find({'timedout': True})
        sa2, = self.db.SessionAnswer.find({'timedout': None})

        sa2.add_date -= datetime.timedelta(seconds=3)
        sa2.save()

        if sa2['question'] == q1['_id']:
            q = q1
        else:
            q = q2

        r = self.post_struct(url, {
          'answer': q['correct'],
          'time': random.random() * 10
        })
        self.assertTrue(r['correct'])

    def test_quizzing_finish(self):
        assert not self.db.QuestionSession.find().count()
        url = self.reverse_url('quizzing')

        def _get():
            return self.get_struct(url, {'category': self.tour_guide['name']})

        for i in range(20):
            self._create_question(self.tour_guide, self.newyork)

        user = self._login(location=self.newyork)
        _one_right = False
        for i in range(QuizzingHandler.NO_QUESTIONS):
            r = _get()
            if i + 1 == QuizzingHandler.NO_QUESTIONS:
                self.assertTrue(r['no_questions']['last'])
            if not _one_right:
                _one_right = True
                answer = 'one'
            else:
                answer = random.choice(['one', 'two', 'three'])
            time_ = random.random() * 10 - 0.1
            r = self.post_struct(url, {'answer': answer, 'time': time_})

        r = self.post_struct(url, {'finish': True})
        assert r['results']
        self.assertTrue(r['results']['coins'])
        self.assertTrue(r['results']['total_points'])




    def test_flying(self):
        url = self.reverse_url('fly')
        sanfran = self.db.Location()
        sanfran['code'] = u'SFO'
        sanfran['city'] = u'San Francisco'
        sanfran['country'] = u'United States'
        sanfran['lat'] = 1.0
        sanfran['lng'] = 2.0
        sanfran.save()
        self.newyork['lat'] = 3.0
        self.newyork['lng'] = 4.0
        self.newyork.save()

        def _get(route):
            return self.get_struct(url, {'route': route})

        r = _get('JFKtoSFO')
        self.assertEqual(r, {'error': 'NOTLOGGEDIN'})
        user = self._login(location=self.newyork)
        user_settings = self.db.UserSettings.find_one({'user': user['_id']})
        user_settings['user'] = user['_id']
        user_settings['coins_total'] = 1000
        user_settings['miles_total'] = 0.0
        user_settings.save()

        r = _get('ABCtoSFO')
        self.assertEqual(r, {'error': 'INVALIDAIRPORT'})

        r = _get('JFKtoABC')
        self.assertEqual(r, {'error': 'INVALIDAIRPORT'})

        r = _get('JFKtoJFK')
        self.assertEqual(r, {'error': 'INVALIDROUTE'})

        r = _get('JFKtoSFO')
        self.assertEqual(r, {'error': 'INVALIDROUTE'})

        user_settings['coins_total'] = 0
        user_settings.save()
        def _post():
            return self.post_struct(url, {'id': str(sanfran['_id'])})

        r = _post()
        self.assertEqual(r['error'], 'CANTAFFORD')

        user_settings['coins_total'] = 1000
        user_settings.save()
        r = _post()
        self.assertEqual(r['to_code'], 'SFO')
        self.assertEqual(r['from_code'], self.newyork['code'])
        cost = r['cost']

        flight = self.db.Flight.find_one({
          'user': user['_id'],
          'from': self.newyork['_id'],
          'to': sanfran['_id'],
        })
        self.assertTrue(flight)

        user = self.db.User.find_one({'_id': user['_id']})
        self.assertEqual(user['current_location'], sanfran['_id'])

        transaction = self.db.Transaction.find_one({
          'user': user['_id'],
          'cost': cost,
          'flight': flight['_id'],
        })
        self.assertTrue(transaction)

        r = _get('JFKtoSFO')
        self.assertEqual(r['to']['lat'], sanfran['lat'])
        self.assertEqual(r['to']['lng'], sanfran['lng'])
        self.assertEqual(r['from']['lat'], self.newyork['lat'])
        self.assertEqual(r['from']['lng'], self.newyork['lng'])
        self.assertTrue(r['miles'])

    def test_coins(self):
        url = self.reverse_url('coins')

        def _get(*a, **k):
            return self.get_struct(url, *a, **k)

        r = _get()
        self.assertEqual(r, {'error': 'NOTLOGGEDIN'})

        user = self._login(location=self.newyork)
        user_settings = self.db.UserSettings()
        user_settings['user'] = user['_id']
        user_settings['coins_total'] = 1000
        user_settings['miles_total'] = 0.0
        user_settings.save()
        r = _get()
        self.assertEqual(r, {})

        sanfran = self.db.Location()
        sanfran['code'] = u'SFO'
        sanfran['city'] = u'San Francisco'
        sanfran['country'] = u'United States'
        sanfran['lat'] = 1.0
        sanfran['lng'] = 2.0
        sanfran.save()

        stockholm = self.db.Location()
        stockholm['code'] = u'ARN'
        stockholm['city'] = u'Stockholm'
        stockholm['country'] = u'Sweden'
        stockholm['lat'] = 0.1
        stockholm['lng'] = 0.2
        stockholm.save()

        f1 = self.db.Flight()
        f1['user'] = user['_id']
        f1['from'] = self.newyork['_id']
        f1['to'] = sanfran['_id']
        f1['miles'] = 1000.0
        f1.save()

        tx1 = self.db.Transaction()
        tx1['user'] = user['_id']
        tx1['cost'] = 100
        tx1['flight'] = f1['_id']
        tx1['add_date'] = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
        tx1.save(update_modify_date=False)

        f2 = self.db.Flight()
        f2['user'] = user['_id']
        f2['from'] = sanfran['_id']
        f2['to'] = stockholm['_id']
        f2['miles'] = 20000.0
        f2.save()

        tx2 = self.db.Transaction()
        tx2['user'] = user['_id']
        tx2['cost'] = 200
        tx2['flight'] = f2['_id']
        tx2.save()

        r = _get({'transactions-page': 0})
        t1 = r['transactions'][0]
        self.assertEqual(t1['cost'], 200)
        self.assertTrue(sanfran['city'] in t1['description'])
        self.assertTrue(stockholm['city'] in t1['description'])
        t2 = r['transactions'][1]
        self.assertEqual(t2['cost'], 100)
        self.assertTrue(self.newyork['city'] in t2['description'])
        self.assertTrue(sanfran['city'] in t2['description'])

        # XXX need to test r['jobs']

    def test_pinpoint(self):
        url = self.reverse_url('pinpoint')
        user = self._login(location=self.newyork)
        user_settings, = self.db.UserSettings.find()

        def _get(data=None):
            return self.get_struct(url, data)

        def _post(data):
            return self.post_struct(url, data)

        c = self.db.PinpointCenter()
        c['country'] = self.newyork['country']
        c['locality'] = self.newyork['locality']
        c['south_west'] = [29.0, -123.0]
        c['north_east'] = [47.0, -67.0]
        c.save()

        r = _get()
        center = r['center']
        self.assertEqual(center['sw'], {
          'lat': 29.0, 'lng': -123.0
        })
        self.assertEqual(center['ne'], {
          'lat': 47.0, 'lng': -67.0
        })

        loc1 = self.db.Location()
        loc1['city'] = u'Buffalo'
        loc1['locality'] = u'New York'
        loc1['country'] = u'United States'
        loc1['lat'] = 30.0
        loc1['lng'] = -80.0
        loc1.save()

        loc2 = self.db.Location()
        loc2['city'] = u'Woodstock'
        loc2['locality'] = u'New York'
        loc2['country'] = u'United States'
        loc2['lat'] = 35.0
        loc2['lng'] = -85.0
        loc2.save()

        locX = self.db.Location()
        locX['city'] = u'Tokoyo'
        locX['country'] = u'Japan'
        locX['lat'] = -5.0
        locX['lng'] = 8.0
        locX.save()

        r = _get({'next': True})
        self.assertTrue(r['question']['seconds'])
        self.assertTrue(r['question']['name'])
        _first_name = r['question']['name']
        _possible_names = [x['city'] for x in
                          self.db.Location.find(
                            {'country': self.newyork['country']})]

        _impossible_names = [x['city'] for x in
                          self.db.Location.find(
                            {'country': {'$ne': self.newyork['country']}})]
        self.assertTrue(r['question']['name'] in _possible_names)
        self.assertTrue(r['question']['name'] not in _impossible_names)

        session, = self.db.PinpointSession.find()

        # time out on the first one, i.e. no post of an answer
        r = _get({'next': True})

        first_a, second_a = (self.db.PinpointAnswer
                             .find({'session': session['_id']})
                             .sort('add_date', 1))
        assert first_a['add_date'] < second_a['add_date']  # sorted done right

        # since a new question has been requested without the previous one
        # having an answer, the first one was simply a matter of it timing out
        self.assertTrue(first_a['timedout'])
        self.assertEqual(first_a['points'], 0.0)

        self.assertTrue(r['question']['name'] in
                        [x for x in _possible_names if x != _first_name])

        # let's send an answer this time
        _correct = self.db.Location.find_one({'city': r['question']['name']})
        data = {
          'lat': _correct['lat'] + 0.1,
          'lng': _correct['lng'] - 0.1,
          'time': '2.1',
        }
        r = _post(data)
        assert self.db.PinpointAnswer.find().count() == 2
        # re-fetch from database
        second_a = self.db.PinpointAnswer.find_one({'_id': second_a['_id']})
#        self.assertEqual(round(second_a['time']), PinpointHandler.SECONDS)
        self.assertEqual(second_a['answer'], [data['lat'], data['lng']])
        self.assertTrue(second_a['points'])

        self.assertEqual(r['correct_position'], {
          'lat': _correct['lat'],
          'lng': _correct['lng'],
        })
        self.assertTrue(r['miles'] < 10)

        # get another question and get it wrong
        r = _get({'next': True})
        _correct = self.db.Location.find_one({'city': r['question']['name']})
        data = {
          'lat': _correct['lat'] + 1.0,
          'lng': _correct['lng'] - 1.0,
          'time': '1.1',
        }
        r = _post(data)
        #self.assertTrue(not r['correct'])
        self.assertEqual(r['correct_position'], {
          'lat': _correct['lat'],
          'lng': _correct['lng'],
        })
        self.assertTrue(r['miles'] > 10)

        for i in range(10):
            self._create_random_location(self.newyork)

        # 4th question
        r = _get({'next': True})
        self.assertEqual(r['no_questions']['total'],
                         PinpointHandler.NO_QUESTIONS)
        self.assertEqual(r['no_questions']['number'], 4)

        _correct = self.db.Location.find_one({'city': r['question']['name']})
        data = {
          'lat': _correct['lat'] + .1,
          'lng': _correct['lng'] - .1,
          'time': 3.3,
        }
        r = _post(data)
        self.assertEqual(_correct['lat'], r['correct_position']['lat'])
        self.assertEqual(_correct['lng'], r['correct_position']['lng'])
        self.assertEqual(r['time'], 3.3)
        self.assertTrue(r['miles'] < 10.)
        self.assertTrue(r['points'] > 0)

        _total_points = 0.0
        _prev_location = None
        for i in range(5, PinpointHandler.NO_QUESTIONS + 1):
            r = _get({'next': True})
            if _prev_location:
                self.assertNotEqual(_prev_location, r['question']['name'])
            _prev_location = r['question']['name']
            assert r['no_questions']['number'] == i
            if i == PinpointHandler.NO_QUESTIONS:
                self.assertTrue(r['no_questions']['last'])
            else:
                self.assertTrue(not r['no_questions']['last'])
            _correct = (self.db.Location
                        .find_one({'city': r['question']['name']}))
            data = {
              # the divide is the assure that the delta is not too big
              # to cause 0 points every single time
              'lat': _correct['lat'] + random.random() / 2,
              'lng': _correct['lng'] - random.random() / 2,
              'time': random.random() * 10 / 2
            }
            r = _post(data)
            _total_points += r['points']

        self.assertTrue(_total_points > 0.0)

        # next, we're suppose to close the finisher
        session, = self.db.PinpointSession.find()
        assert session['center'] == self.newyork['_id']
        assert session['user'] == user['_id']

        r = _post({'finish': True})
        session, = self.db.PinpointSession.find()
        self.assertTrue(session['finish_date'])

        #session, = self.db.PinpointSession.find()
        total_points = 0.0
        for answer in self.db.PinpointAnswer.find({'session': session['_id']}):
            total_points += answer['points']
        self.assertTrue(r['results'])
        self.assertTrue(r['results']['total_points'])
        self.assertTrue(r['results']['coins'])

        # that should have incremented the user_settings's coins_total
        coins_total_before = user_settings['coins_total']
        user_settings, = self.db.UserSettings.find()
        coins_total_after = user_settings['coins_total']
        self.assertEqual(coins_total_after - coins_total_before,
                         r['results']['coins'])

        job, = self.db.Job.find()
        assert job['user'] == user['_id']
        self.assertTrue(job['category'])
        self.assertEqual(coins_total_after - coins_total_before,
                         job['coins'])
        self.assertEqual(job['location'], self.newyork['_id'])

    def test_pinpoint_timeout_last(self):
        for __ in range(20):
            self._create_random_location(self.newyork)

        def _get(data=None):
            return self.get_struct(url, data)

        def _post(data):
            return self.post_struct(url, data)

        url = self.reverse_url('pinpoint')
        user = self._login(location=self.newyork)

        c = self.db.PinpointCenter()
        c['country'] = self.newyork['country']
        c['locality'] = self.newyork['locality']
        c['south_west'] = [29.0, -123.0]
        c['north_east'] = [47.0, -67.0]
        c.save()

        # before we begin, insert a previous session so that the tests make
        # sure that doesn't affect anything
        s = self.db.PinpointSession()
        s['center'] = c['_id']
        s['user'] = user['_id']
        s['finish_date'] = (datetime.datetime.utcnow()
                            - datetime.timedelta(days=1))
        s.save()

        r = _get()
        assert r['center']
        assert 'question' not in r

        for i in range(PinpointHandler.NO_QUESTIONS - 1):
            r = _get({'next': True})
            assert r['question']
            _correct = self.db.Location.find_one({'city': r['question']['name']})
            data = {
              'lat': _correct['lat'] + 0.1,
              'lng': _correct['lng'] - 0.1,
              'time': '0.1',
            }
            r = _post(data)
            assert r['miles']
            assert r['time'] > 0

        # last question
        r = _get({'next': True})
        assert r['no_questions']['last']

        # now, for the 10th question, there's no post() because it times out
        # so the next thing will be a get(finish=True)
        r = _post({'finish': True})
        self.assertTrue(r['results']['total_points'])
        self.assertTrue(r['results']['coins'])
        user_settings, = self.db.UserSettings.find()
        answers = self.db.PinpointAnswer.find()
        last_answer, = answers.sort('add_date', -1).limit(1)
        self.assertTrue(last_answer['timedout'])
        self.assertEqual(last_answer['points'], 0.0)
        session, prev_session = (self.db.PinpointSession
                                 .find().sort('finish_date', -1))
        assert session['finish_date'] > prev_session['finish_date']
        self.assertTrue(session['finish_date'])

    def _create_random_location(self, near):
        def random_str(l):
            pool = list(u'qwertyuiopasdfghjklzxcvbnm')
            random.shuffle(pool)
            return ''.join(pool[:l])

        loc = self.db.Location()
        loc['country'] = near['country']
        loc['locality'] = near['locality']
        loc['city'] = random_str(10).title()
        loc['lat'] = near['lat'] + random.choice([-10, -5, -1, 1, 5, 10])
        loc['lng'] = near['lng'] + random.choice([-10, -5, -1, 1, 5, 10])
        loc.save()

    def test_settings(self):
        self._login()
        url = self.reverse_url('settings')
        r = self.get_struct(url)
        self.assertEqual(r['disable_sound'], False)

        r = self.post_struct(url, {'disable_sound': True})
        self.assertEqual(r['disable_sound'], True)

        r = self.get_struct(url)
        self.assertEqual(r['disable_sound'], True)

        r = self.post_struct(url, {'disable_sound': ''})
        self.assertEqual(r['disable_sound'], False)

        r = self.get_struct(url)
        self.assertEqual(r['disable_sound'], False)

    def test_miles(self):
        user = self._login()
        url = self.reverse_url('miles')
        r = self.get_struct(url)
        self.assertEqual(r['flights'], [])
        self.assertEqual(r['no_cities'], 1)
        self.assertEqual(r['percentage'], 0)

        # now pretend we've done some flights
        loc1 = self.db.Location()
        loc1['city'] = u'Kansas City'
        loc1['country'] = u'United States'
        loc1['code'] = u'MCI'
        loc1['airport_name'] = u'Kansas City International Airport'
        loc1['lat'] = 30.0
        loc1['lng'] = -80.0
        loc1.save()

        f1 = self.db.Flight()
        f1['user'] = user['_id']
        f1['from'] = self.newyork['_id']
        f1['to'] = loc1['_id']
        f1['miles'] = 1000.0
        f1.save()

        r = self.get_struct(url)
        self.assertEqual(r['no_cities'], 2)
        data, = r['flights']
        self.assertTrue(data['date'])
        self.assertEqual(data['miles'], 1000)
        self.assertEqual(data['from']['code'], self.newyork['code'])
        self.assertEqual(data['from']['airport_name'], self.newyork['airport_name'])
        self.assertEqual(data['from']['name'], unicode(self.newyork))
        self.assertEqual(data['to']['code'], loc1['code'])
        self.assertEqual(data['to']['airport_name'], loc1['airport_name'])
        self.assertEqual(data['to']['name'], unicode(loc1))
        #self.assertEqual(r['percentage'], 0)

    def test_airport(self):
        # XXX: commented out since this now depends on there being enough questions
        return
        self._login(location=self.newyork)
        url = self.reverse_url('airport')

        r = self.get_struct(url)
        self.assertEqual(r['airport_name'], self.newyork['airport_name'])
        self.assertTrue(r['destinations'][-1]['id'], 'moon')
        non_moons = [x for x in r['destinations'] if x['id'] != 'moon']
        self.assertEqual(non_moons, [])

        loc1 = self.db.Location()
        loc1['city'] = u'Kansas City'
        loc1['country'] = u'United States'
        loc1['code'] = u'MCI'
        loc1['airport_name'] = u'Kansas City International Airport'
        loc1['lat'] = self.newyork['lat'] + 1
        loc1['lng'] = self.newyork['lng'] + 1
        loc1.save()

        loc2 = self.db.Location()
        loc2['city'] = u'Vancouver'
        loc2['country'] = u'Canada'
        loc2['code'] = u'YVR'
        loc2['airport_name'] = u'Vancouver International Airport'
        loc2['lat'] = self.newyork['lat'] + 10
        loc2['lng'] = self.newyork['lng'] + 10
        loc2.save()

        locX = self.db.Location()
        locX['city'] = u'Charleston'
        locX['country'] = u'United States'
        locX['lat'] = -5.0
        locX['lng'] = 8.0
        locX.save()

        r = self.get_struct(url)
        cities = [x['city'] for x in r['destinations'] if x['id'] != 'moon']
        self.assertEqual(cities[0], loc1['city'])
        # order by distance
        self.assertEqual(cities[1], loc2['city'])
        self.assertTrue(locX['city'] not in cities)  # no airport_name
        self.assertTrue(r['destinations'][-1]['id'], 'moon')

    def test_city_ambassadors(self):
        loc = self.db.Location()
        loc['country'] = u'Unheardof'
        loc['city'] = u'Place'
        loc['lat'] = 1.0
        loc['lng'] = 1.0
        loc.save()
        self._login(location=loc)
        url = self.reverse_url('city')
        response = self.get_struct(url, {'get': 'ambassadors'})
        self.assertEqual(response['ambassadors'], None)

        user = self.db.User()
        user['username'] = u'karl'
        user.save()

        ambassador = self.db.Ambassador()
        ambassador['user'] = user['_id']
        ambassador['country'] = loc['country']
        ambassador.save()

        document = self.db.HTMLDocument()
        document['source'] = u'Check *this* out!'
        document['source_format'] = u'markdown'
        document['type'] = u'ambassadors'
        document['country'] = loc['country']
        document['user'] = user['_id']
        document.save()

        response = self.get_struct(url, {'get': 'ambassadors'})
        self.assertTrue(u'Check <em>this</em> out!' in response['ambassadors'])

    def test_signup_upon_invitation(self):
        user = self._login(u'karl', email=u'karl@example.com',
                           first_name=u'Karl', last_name=u'Ekberg')
        assert user

        invitation = self.db.Invitation()
        invitation['user'] = user['_id']
        invitation['email'] = u'Peter@example.com'
        invitation.save()

        self._login(username=u'peter', email=u'peter@example.com')
        email_sent = mail.outbox[-1]
        self.assertTrue(email_sent.from_email.startswith('noreply'))
        self.assertEqual(email_sent.recipients(), [user['email']])
        self.assertTrue('peter' in email_sent.subject)
        from core.handlers import BaseAuthHandler
        self.assertTrue(str(BaseAuthHandler.INVITATION_AWARD)
                        in email_sent.body)
        assert email_sent.body  # not decided what to actually test yet

        job, = self.db.Job.find()
        category = self.db.Category.find_one({'_id': job['category']})
        self.assertEqual(category['name'], 'Recruiter')
        self.assertEqual(job['coins'], BaseAuthHandler.INVITATION_AWARD)

        # if 'peter' logs in again, it should be awarded a second time
        emails_before = len(mail.outbox)
        self._login(username=u'peter', email=u'peter@example.com')
        emails_after = len(mail.outbox)
        self.assertEqual(emails_before, emails_after)

    def test_city(self):
        user = self._login(location=self.newyork)
        url = self.reverse_url('city')
        structure = self.get_struct(url)
        self.assertEqual(structure['count_messages'], 0)
        data = {
          'message': "Hi it's me",
        }
        structure = self.post_struct(url, data)
        messages = structure['messages']
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['time_ago'], 'seconds')
        self.assertEqual(messages[0]['message'], data['message'])
