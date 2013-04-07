#!/usr/bin/env python
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

    now = datetime.datetime.utcnow()
    then = now - datetime.timedelta(days=100)
    users = (
        db.User
        .find({'modify_date': {'$lt': then}, 'anonymous': True})
        .sort('modify_date')
        #.limit(100)# temporary
    )
    delete_ids = []
    leave_models = (
        db.Flight,
        db.Job,
        db.QuestionSession,
        db.Feedback,
    )
    check_models = (
        db.Transaction,
        db.Invitation, db.Friendship,
        db.FriendshipToken,
    )
    delete_models = (
        db.TotalEarned,
        db.UserSettings,
        db.ErrorEvent,
    )
    count = 0
    for user in users:
        leave = False
        for model in leave_models:
            if model.collection.find({'user': user['_id']}).count():
                leave = True
                break
        if leave:
            continue
        for model in check_models:
            assert not model.collection.find({'user': user['_id']}).count(), model

        for model in delete_models:
            for each in model.find({'user': user['_id']}):
                each.delete()
        db.User.find_one({'_id': user['_id']}).delete()
        count += 1
        print now - user['modify_date']

    print "DELETED", count, "unused users"


if __name__ == '__main__':
    run()
