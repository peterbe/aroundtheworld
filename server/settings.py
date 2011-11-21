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

try:
    from local_settings import *
except ImportError:
    pass


#assert TWITTER_CONSUMER_KEY
#assert TWITTER_CONSUMER_SECRET
