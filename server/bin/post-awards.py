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
                       'type': handlers.AWARDTYPE_SIGNIN})
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
        #print "**** SIGNIN AWARD ****"
        #return
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

    def create_10k_award(user, user_settings):
        assert user_settings
        location = db.Location.find_one({'_id': user['current_location']})
        assert location
        reward = 75
        data = {}
        data['miles'] = 10000
        award = db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 10,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = handlers.AWARDTYPE_10KMILES
        award['reward'] = reward
        award.save()

        user_settings['coins_total'] += reward
        user_settings.save()

    def create_50k_award(user, user_settings):
        assert user_settings
        location = db.Location.find_one({'_id': user['current_location']})
        assert location
        reward = 150
        data = {}
        data['miles'] = 50000
        award = db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 50,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = handlers.AWARDTYPE_50KMILES
        award['reward'] = reward
        award.save()

        user_settings['coins_total'] += reward
        user_settings.save()

    def create_100k_award(user, user_settings):
        assert user_settings
        location = db.Location.find_one({'_id': user['current_location']})
        assert location
        reward = 500
        data = {}
        data['miles'] = 100000
        award = db.Award()
        award['user'] = user['_id']
        award['description'] = u'Flying over 100,000 miles'
        award['data'] = data
        award['location'] = location['_id']
        award['type'] = handlers.AWARDTYPE_100KMILES
        award['reward'] = reward
        award.save()

        user_settings['coins_total'] += reward
        user_settings.save()

    def has_10k_award(user):
        return (db.Award
                .find({'user': user['_id'],
                       'type': handlers.AWARDTYPE_10KMILES})
                .count())

    def has_50k_award(user):
        return (db.Award
                .find({'user': user['_id'],
                       'type': handlers.AWARDTYPE_50KMILES})
                .count())

    def has_100k_award(user):
        return (db.Award
                .find({'user': user['_id'],
                       'type': handlers.AWARDTYPE_100KMILES})
                .count())


    tutorial_awards = 0
    signin_awards = 0
    count_10k_awards = 0
    count_50k_awards = 0
    count_100k_awards = 0

    for user in db.User.find():
        try:
            anonymous = user['anonymous']
        except KeyError:
            user['anonymous'] = False
            anonymous = False
            #user.save()
        print user['username'],
        user_settings = db.UserSettings.find_one({'user': user['_id']})
        print int(user_settings['miles_total']), "miles"

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

        if user_settings['miles_total'] > 10000:
            if not has_10k_award(user):
                create_10k_award(user, user_settings)
                count_10k_awards += 1
        if user_settings['miles_total'] > 50000:
            if not has_50k_award(user):
                create_50k_award(user, user_settings)
                count_50k_awards += 1
        if user_settings['miles_total'] > 100000:
            if not has_100k_award(user):
                create_100k_award(user, user_settings)
                count_100k_awards += 1

        print

    print "NEW SIGNIN AWARDS:", signin_awards
    print "NEW TUTORIAL AWARDS:", tutorial_awards
    print "NEW 10K AWARDS:", count_10k_awards
    print "NEW 50K AWARDS:", count_50k_awards
    print "NEW 100K AWARDS:", count_100k_awards


if __name__ == '__main__':
    run()
