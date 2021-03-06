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

NOREPLY_EMAIL = 'noreply@aroundtheworldgame.com'

SIGNATURE = '%s\nhttp://aroundtheworldgame.com' % PROJECT_TITLE

THUMBNAIL_DIRECTORY = path('static/thumbnails')
QUIZ_MIN_NO_QUESTIONS = 10
PINPOINT_NO_QUESTIONS = 10
QUIZ_NO_QUESTIONS_TUTORIAL = 4

COOKIE_SECRET = ""

PICTURE_QUESTION_WIDTH_HEIGHT = (250, 250)
FOUR_PICTURES_WIDTH_HEIGHT = (170, 170)

GOOGLE_MAPS_API_KEY = ''

try:
    from local_settings import *
except ImportError:
    pass
assert COOKIE_SECRET, "It must be set in local_settings.py"

assert FILEPICKER_API_KEY
assert TWITTER_CONSUMER_KEY
assert TWITTER_CONSUMER_SECRET
