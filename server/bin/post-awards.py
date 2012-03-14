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

    def has_signin_award(user):
        return (db.Award
                .find({'user': user['_id'],
                       'type': handlers.AWARDTYPE_TUTORIAL})
                .count())

    def create_signin_award(user):
        user_settings = db.UserSettings.find_one({'user': user['_id']})
        assert user_settings
        location = db.Location.find_one({'_id': user['current_location']})
        assert location
        reward = 100
        data = {}
        data['sign_in'] = True
        award = db.Award()
        award['user'] = user['_id']
        award['description'] = u'Signing in properly'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = handlers.AWARDTYPE_SIGNIN
        award['reward'] = reward
        award.save()

        user_settings['coins_total'] += reward
        user_settings.save()

    nomansland = db.Location.find_one({'code': '000'})
    assert nomansland
    tutorial = db.Category.find_one({'name': 'Tutorial'})
    assert tutorial

    def has_left_tutorial(user):
        return (db.Flight
                .find({'from': nomansland['_id'], 'user': user['_id']})
                .count())

    def has_tutorial_award(user):
        return (db.Award
                .find({'user': user['_id'],
                       'type': handlers.AWARDTYPE_TUTORIAL})
                .count())

    def create_tutorial_award(user):
        user_settings = db.UserSettings.find_one({'user': user['_id']})
        assert user_settings
        location = nomansland
        reward = 50
        data = {}
        data['finishing_tutorial'] = True
        award = db.Award()
        award['user'] = user['_id']
        award['description'] = u'Finishing the tutorial'
        award['data'] = data
        award['location'] = location['_id']
        award['category'] = tutorial['_id']
        award['type'] = handlers.AWARDTYPE_TUTORIAL
        award['reward'] = reward
        award.save()

        user_settings['coins_total'] += reward
        user_settings.save()


    tutorial_awards = 0
    signin_awards = 0

    for user in db.User.find():
        try:
            anonymous = user['anonymous']
        except KeyError:
            user['anonymous'] = False
            anonymous = False
            #user.save()
        print user['username']
        if not anonymous:
            print "\tnot anonymous"
            if not has_signin_award(user):
                print "\t\tCREATE SIGNIN AWARD"
                create_signin_award(user)
                signin_awards += 1
            else:
                print "\t\talready has signin award"
        else:
            print "\tstill anonymous"

        if has_left_tutorial(user):
            print "\thas left tutorial"
            if not has_tutorial_award(user):
                print "\t\tCREATE TUTORIAL AWARD"
                create_tutorial_award(user)
                tutorial_awards += 1
            else:
                print "\t\talready has tutorial award"
        else:
            print "\thas NOT left tutorial"
        print

    print "NEW SIGNIN AWARDS:", signin_awards
    print "NEW TUTORIAL AWARDS:", tutorial_awards


if __name__ == '__main__':
    run()
