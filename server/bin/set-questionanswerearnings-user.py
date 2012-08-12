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
    print db.QuestionAnswerEarning.find({'user': None}).count()
    print db.QuestionAnswerEarning.find({'user': {'$ne': None}}).count()
    _questions = {}
    for each in db.QuestionAnswerEarning.find({'user': None}):
        if each['question'] not in _questions:
            question = db.Question.find_one({'_id': each['question']})
            _questions[each['question']] = question['author']
        each['user'] = _questions[each['question']]
        each.save()


if __name__ == '__main__':
    run()
