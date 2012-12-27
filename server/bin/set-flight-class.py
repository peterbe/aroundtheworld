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

    c = 0

    for each in db.Flight.find({'class': {'$exists': False}}):
        each['class'] = 2
        c += 1
        each.save()

    print c, "flights fixed"


if __name__ == '__main__':
    run()
