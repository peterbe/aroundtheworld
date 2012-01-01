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
        newyork['city'] = u'New York City'
        newyork['country'] = u'United States'
        newyork.save()
        self.newyork = newyork

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

    def _create_question(self, location):
        q = self.db.Question()
        q['text'] = (u'(%s) What number question is this?' %
                     (self.db.Question.find().count() + 1,))
        q['correct'] = u'one'
        q['alternatives'] = [u'one', u'two', u'three']
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
        q = self.get_struct(url)
        self.assertEqual(q, {'error': 'NOTLOGGEDIN'})
        user = self._login(location=self.newyork)

        q = self.get_struct(url)
        self.assertEqual(q, {'error': 'NOQUESTIONS'})

        q1 = self._create_question(self.newyork)
        q2 = self._create_question(self.newyork)
        r = self.get_struct(url)
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
        r = self.get_struct(url)
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
