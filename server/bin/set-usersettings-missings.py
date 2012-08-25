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

    for each in db.UserSettings.find({'was_anonymous': {'$exists': False}}):
        each['was_anonymous'] = False
        each.save()


if __name__ == '__main__':
    run()
