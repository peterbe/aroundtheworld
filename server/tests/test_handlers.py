import datetime
import os
import json
from urllib import urlencode
import tornado.escape
from pymongo.objectid import ObjectId
from .base import BaseHTTPTestCase
import settings
#from handlers import (TwitterAuthHandler, FollowsHandler, FollowingHandler,
#                      EveryoneIFollowJSONHandler)

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
        newyork.save()
        self.newyork = newyork

        tour_guide = self.db.Category()
        tour_guide['name'] = u'Tour guide'
        tour_guide.save()
        self.tour_guide = tour_guide

    def _login(self, username=u'peterbe', email='mail@peterbe.com',
               client=None, location=None):
        user = self.db.User.one(dict(username=username))
        if client is None:
            client = self.client
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
        self.assertTrue(settings.PROJECT_TITLE in response.body)

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
        q = r['question']
        self.assertTrue(q['text'] in (q1['text'], q2['text']))
        qs, = self.db.QuestionSession.find()  # assert there is only 1
        self.assertEqual(qs['user'], user['_id'])
        self.assertEqual(qs['location'], self.newyork['_id'])

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

        sa1, = self.db.SessionAnswer.find({'timedout': True})
        sa2, = self.db.SessionAnswer.find({'timedout': None})

        sa2.add_date -= datetime.timedelta(seconds=3)
        sa2.save()

        if sa2['question'] == q1['_id']:
            q = q1
        else:
            q = q2

        r = self.post_struct(url, {'answer': q['correct'], 'id': str(q['_id'])})
        self.assertTrue(r['correct'])

    def test_flying(self):
        url = self.reverse_url('fly')
        sanfran = self.db.Location()
        sanfran['code'] = u'SFO'
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
        user_settings = self.db.UserSettings()
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

        def _get():
            return self.get_struct(url)

        r = _get()
        self.assertEqual(r, {'error': 'NOTLOGGEDIN'})

        user = self._login(location=self.newyork)
        user_settings = self.db.UserSettings()
        user_settings['user'] = user['_id']
        user_settings['coins_total'] = 1000
        user_settings['miles_total'] = 0.0
        user_settings.save()
        r = _get()
        self.assertEqual(r['transactions'], [])

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

        r = _get()
        t1 = r['transactions'][0]
        self.assertEqual(t1['cost'], 100)
        self.assertTrue(self.newyork['city'] in t1['description'])
        self.assertTrue(sanfran['city'] in t1['description'])
        t2 = r['transactions'][1]
        self.assertEqual(t2['cost'], 200)
        self.assertTrue(sanfran['city'] in t2['description'])
        self.assertTrue(stockholm['city'] in t2['description'])

        #self.assertEqual(r['transactions'], [])
