import os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)

PROJECT_TITLE = u"Around The World"
DATABASE_NAME = "aroundtheworld"

TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# complete this in your local_settings.py to get emails sent on errors
ADMIN_EMAILS = (
)

NOREPLY_EMAIL = 'noreply@aroundtheworld.peterbe.com'

SIGNATURE = PROJECT_TITLE

THUMBNAIL_DIRECTORY = path('static/thumbnails')
QUIZ_MIN_NO_QUESTIONS = 10
PINPOINT_NO_QUESTIONS = 10
QUIZ_NO_QUESTIONS_TUTORIAL = 3

COOKIE_SECRET = ""

try:
    from local_settings import *
except ImportError:
    pass
assert COOKIE_SECRET, "It must be set in local_settings.py"

#assert TWITTER_CONSUMER_KEY
#assert TWITTER_CONSUMER_SECRET
