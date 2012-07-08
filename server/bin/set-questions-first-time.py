#!/usr/bin/env python
from random import randint
import cPickle
import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

from core import handlers
from core.models import *
import settings

def run():
    db = connection[settings.DATABASE_NAME]
    #for sa in db.SessionAnswer.find({'first_time': None}):
    #    sa['first_time'] = False
    #    sa['first_time_correct'] = False
    #    sa.save()

    try:
        users_done = cPickle.load(open('processed-users.pickle', 'rb'))
    except IOError:
        users_done = set()

    no_users = db.User.collection.find().count()
    left = no_users - len(users_done)
    print "LEFT", left
    filter_ = {}
    if users_done:
        filter_ = {'_id': {'$nin': list(users_done)}}

    _questions = {}
    _locations = {}
    _categories = {}
    for user in (db.User.collection
                .find(filter_)
                .limit(200)):
        print (user['username'] + ' ').ljust(79, '-')
        questions = set()
        questions_right = set()
        for s in (db.QuestionSession.collection
                  .find({'user': user['_id'],
                         'finish_date': {'$ne': None}})
                  .sort('add_date')):
            print s['add_date'], db.SessionAnswer.find({'session': s['_id']}).count()
            if s['category'] not in _categories:
                _categories[s['category']] = db.Category.find_one({'_id': s['category']})
            print _categories[s['category']],
            if s['location'] not in _locations:
                _locations[s['location']] = db.Location.find_one({'_id': s['location']})
            print _locations[s['location']]
            for a in db.SessionAnswer.find({'session': s['_id']}):
                if a['question'] not in _questions:
                    _questions[a['question']] = db.Question.find_one({'_id': a['question']})
                q = _questions[a['question']]
                print "\t", repr(q['text'][:40]), a['correct'],
                if a['question'] not in questions:
                    print "FIRST TIME!",
                    a['first_time'] = True
                    questions.add(a['question'])
                else:
                    a['first_time'] = False
                if a['correct'] and a['question'] not in questions_right:
                    a['first_time_correct'] = True
                    print "CORRECT!",
                    questions_right.add(a['question'])
                else:
                    a['first_time_correct'] = False
                print
                a.save()

        users_done.add(user['_id'])
        cPickle.dump(users_done, open('processed-users.pickle', 'wb'))


if __name__ == '__main__':
    run()
