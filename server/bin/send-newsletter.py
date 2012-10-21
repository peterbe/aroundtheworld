#!/usr/bin/env python
import os
from random import randint
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

import tornado.options
import tornado.template
from tornado.options import define, options
from tornado_utils.send_mail import send_email
from core import handlers
from core.models import *
import settings


define("subject", type=str)
define("messagetemplate", type=str)
define("dry_run", type=bool, default=False)
define("only_email_addresses", type=str, default='',
       help="Comma separated list of email addresses to send to")

def run(options):
    db = connection[settings.DATABASE_NAME]

    only_email_addresses = options.only_email_addresses
    only_email_addresses = [
        x.strip() for x in only_email_addresses.split(',')
        if x.strip()
    ]
    subject = options.subject
    template_filename = os.path.abspath(os.path.normpath(options.messagetemplate))
    template_code = open(template_filename).read()
    template = tornado.template.Template(template_code)
    log_filename = options.messagetemplate + '.log'
    try:
        done_user_ids = [
            x.strip() for x in open(log_filename).read().splitlines()
            if x.strip()
        ]
    except IOError:
        done_user_ids = []

    unsubscribers = [
      x['user'] for x
      in db.UserSettings.find({'unsubscribe_emails': True}, ('user',))
    ]
    _locations = {}

    for user in db.User.find({'email': {'$ne': None}}):
        if not user['email'] or user['_id'] in unsubscribers:
            continue
        if str(user['_id']) in done_user_ids:
            print "Skipping", user['email']
        if only_email_addresses:
            if user['email'] in only_email_addresses:
                print "ONLY", user['email']
            else:
                continue

        if user['current_location'] not in _locations:
            _locations[user['current_location']] = (
                db.Location.find_one({'_id': user['current_location']})
            )
        user_settings = db.UserSettings.find_one({'user': user['_id']})
        assert user_settings
        data = {
            'SIGNATURE': settings.SIGNATURE,
            'user': user,
            'user_settings': user_settings,
            'current_location': _locations[user['current_location']],
            'unsubscribe_uri': '/unsubscribe/%s' % user.tokenize_id(user['_id'], 12)
        }
        body = template.generate(**data)
        if options.dry_run:
            email_backend = 'tornado_utils.send_mail.backends.console.EmailBackend'
        else:
            email_backend = 'tornado_utils.send_mail.backends.pickle.EmailBackend'

        send_email(
            email_backend,
            subject,
            body,
            settings.ADMIN_EMAILS[0],
            [user['email']],
        )
        if not options.dry_run:
            open(log_filename, 'a').write('%s\n' % user['_id'])
        else:
            print "emailed", user['email']


if __name__ == '__main__':
    tornado.options.parse_command_line()
    run(options)
