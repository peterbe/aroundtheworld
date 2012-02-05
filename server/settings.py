import os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)

PROJECT_TITLE = u"Around The World"
DATABASE_NAME = "aroundtheworld"

COOKIE_SECRET = "12orTzK2XqaGeYdkL3gmUejIFuY37EQn92XsTo2v/Vi="
TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# complete this in your local_settings.py to get emails sent on errors
ADMIN_EMAILS = (
)

THUMBNAIL_DIRECTORY = path('static/thumbnails')

try:
    from local_settings import *
except ImportError:
    pass


#assert TWITTER_CONSUMER_KEY
#assert TWITTER_CONSUMER_SECRET
