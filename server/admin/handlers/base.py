import os
import time
import urllib
from pprint import pprint
import datetime
from collections import defaultdict
import tornado.web
from tornado_utils.routes import route
from core.handlers import BaseHandler as CoreBaseHandler
from tornado_utils.timesince import smartertimesince
from admin.utils import truncate_text
from core.handlers import QuizzingHandler


class djangolike_request_dict(dict):
    def getlist(self, key):
        return self.get(key)


class BaseHandler(CoreBaseHandler):

    LIMIT = 20

    def render(self, template, **options):
        options['current_url'] = self.request.path
        user = self.get_current_user()
        options['is_mayor'] = options['is_ambassador'] = False
        options['is_superuser'] = user['superuser']
        if not options['is_superuser']:
            options['is_ambassador'] = (self.db.Ambassador
                                        .find({'user': user['_id']})
                                        .count())
        options['messages'] = self.pull_flash_messages()
        return super(BaseHandler, self).render(template, **options)

    def trim_all_pages(self, sequence, page, max_length=15):
        if len(sequence) < max_length:
            return
        popped_end = popped_start = False
        mid = len(sequence) / 2
        end = sequence[-1]
        start = sequence[0]
        while len(sequence) > max_length:
            if sequence.index(page) < sequence.index(mid):
                sequence.pop(-1)
                popped_end = True
            else:
                sequence.pop(0)
                popped_start = True
            mid = sequence[len(sequence) / 2]
        if popped_end:
            sequence.append(end)
        if popped_start:
            sequence.insert(0, start)

    def push_flash_message(self, title, text=u'', user=None,
                           type_='info'  # 'success' or 'error'
                           ):
        if user is None:
            user = self.get_current_user()
            assert user
            #if not user:
            #    return
        if not text:
            raise ValueError(
               "AT the moment we can't accept blank texts on flash "\
               "messages because gritter won't be able to show it")
        for msg in (self.db.FlashMessage
                    .find({'user': user['_id']})
                    .sort('add_date', -1)
                    .limit(1)):
            if msg['title'] == title and msg['text'] == text:
                # but was it several seconds ago?
                if (datetime.datetime.utcnow() - msg['add_date']).seconds < 3:
                    return
        msg = self.db.FlashMessage()
        msg['user'] = user['_id']
        msg['title'] = unicode(title)
        msg['text'] = unicode(text)
        msg['type'] = unicode(type_)
        msg.save()

    def pull_flash_messages(self, unread=True, user=None):
        if user is None:
            user = self.get_current_user()
            assert user
            #if not user:
            #    return []
        _search = {'user': user['_id']}
        if unread:
            _search['read'] = False
        messages = []
        for message in self.db.FlashMessage.find(_search).sort('add_date', 1):
            messages.append(message)
            message['read'] = True
            message.save()
        return messages


class AuthenticatedBaseHandler(BaseHandler):
    MAYOR_OK = True
    AMBASSADOR_OK = True

    def prepare(self):
        user = self.get_current_user()
        if not user:
            self.redirect('/#login')
        elif not user['superuser']:
            # check that you're ambassador or mayor
            if self.AMBASSADOR_OK and (self.db.Ambassador
                                       .find({'user': user['_id']})
                                       .count()):
                return
            if self.MAYOR_OK and (self.db.Mayor
                                  .find({'user': user['_id']})
                                  .count()):
                return
            self.redirect(self.reverse_url('admin_ohno'))


class AmbassadorBaseHandler(AuthenticatedBaseHandler):

    MAYOR_OK = False
    AMBASSADOR_OK = True


class SuperuserBaseHandler(AuthenticatedBaseHandler):

    MAYOR_OK = False
    AMBASSADOR_OK = False


@route('/admin/ohno/', name='admin_ohno')
class OhNoAdminHandler(BaseHandler):
    def get(self):
        self.render('admin/ohno.html')


@route('/admin/become/', name='admin_become')
class BecomeAdminHandler(BaseHandler):
    def get(self):
        if not self.application.settings['debug']:
            raise tornado.web.HTTPError(403, "not right now")
        search = self.get_argument('search').lower()
        found_user = None
        for user in self.db.User.find():
            if (user['username'].lower().startswith(search) or
                user['email'].lower().startswith(search)):
                if found_user:
                    raise tornado.web.HTTPError(400, "found more than one")
                found_user = user
        if not found_user:
            raise tornado.web.HTTPError(404, "found none")
        self.set_secure_cookie("user", str(found_user['_id']), expires_days=1)

        #self.write('cool\n')
        #self.finish()
        self.redirect(self.reverse_url('admin_home'))


@route('/admin/', name='admin_home')
class HomeAdminHandler(AuthenticatedBaseHandler):

    def get(self):
        options = {}
        options['count_questions_published'] = (
          self.db.Question
           .find({'published': True})
           .count()
        )
        options['count_questions_not_published'] = (
          self.db.Question
           .find({'published': False})
           .count()
        )
        options['count_locations_available'] = (
          self.db.Location
          .find({'available': True})
          .count()
        )
        options['count_locations_total'] = (
          self.db.Location
          .find()
          .count()
        )
        options['count_countries'] = len(
          self.db.Location
          .find().distinct('country')
        )
        options['count_users'] = (
          self.db.User
          .find()
          .count()
        )
        options['count_jobs'] = (
          self.db.Job
          .find()
          .count()
        )
        tutorial = self.db.Category.find_one({'name': 'Tutorial'})
        assert tutorial
        options['count_jobs_tutorial'] = (
          self.db.Job
          .find({'category': tutorial['_id']})
          .count()
        )
        options['total_miles'] = (
          sum(int(x['miles']) for x in self.db.Flight.collection
                                        .find(None, ('miles',)))
        )
        options['total_coins'] = (
          sum(x['coins'] for x in self.db.Job.collection
                                   .find(None, ('coins',)))
          +
          sum(x['coins'] for x in self.db.QuestionAnswerEarning.collection
                                   .find(None, ('coins',)))
        )
        options['count_users_anonymous'] = (
          self.db.User
          .find({'anonymous': True})
          .count()
        )
        options['latest_user'] = (
          list(self.db.User.find()
          .sort('add_date', -1)
          .limit(1))[0]
        )
        options['count_ambassadors'] = len(
          self.db.Ambassador
          .find().distinct('user')
        )
        options['count_mayors'] = len(
          self.db.Mayor
          .find().distinct('user')
        )

        self.render('admin/home.html', **options)


@route('/admin/news.json', name='admin_news')
class NewsAdminHandler(AuthenticatedBaseHandler):

    MIN_ITEMS = 30
    CUTOFF_DELTA = 60 * 60 * 24
    MAX_ITERATIONS = 5

    def get(self, cutoff_seconds=None, max_date=None, iteration=0):
        items = []
        if cutoff_seconds is None:
            cutoff_seconds = self.CUTOFF_DELTA

        no_items = int(self.get_argument('items', self.MIN_ITEMS))
        now = datetime.datetime.utcnow()
        cutoff = now - datetime.timedelta(seconds=cutoff_seconds)
        filter_ = {'add_date': {'$gt': cutoff}}
        if max_date:
            filter_['add_date']['$lt'] = max_date

        _categories = {}
        _locations = {}
        for model in (self.db.User,
                      self.db.Feedback,
                      self.db.Question,
                      self.db.Award,
                      self.db.HTMLDocument):
            objects = model.collection.find(filter_).sort('add_date', -1)
            for item in objects:
                items.append({
                  # send our dict of categories/locations to prevent excessive
                  # lookups inside get_summary()
                  'summary': self.get_summary(item, model,
                                              categories=_categories,
                                              locations=_locations),
                  'url': self.get_url(item, model),
                  'ts': time.mktime(item['add_date'].timetuple()),
                  'date': smartertimesince(item['add_date'], now=now),
                })
        items.sort(lambda x, y: cmp(y['ts'], x['ts']))
        if len(items) > no_items:
            items = items[:no_items]

        if len(items) < no_items and iteration < self.MAX_ITERATIONS:
            items.extend(self.get(
              cutoff_seconds=cutoff_seconds + self.CUTOFF_DELTA,
              max_date=cutoff,
              iteration=iteration + 1
            ))

        if max_date is None:
            self.write({'items': items})
        else:
            return items

    def get_url(self, item, model):
        if model is self.db.User:
            return self.reverse_url('admin_user_journey', item['_id'])

        if model is self.db.Feedback:
            return self.reverse_url('admin_feedbacks')

        if model is self.db.Question:
            return self.reverse_url('admin_question', item['_id'])

        if model is self.db.HTMLDocument:
            return self.reverse_url('admin_document', item['_id'])

        if model is self.db.Award:
            return self.reverse_url('admin_awards')

        raise NotImplementedError(model._obj_class)

    def get_summary(self, item, model, categories=None, locations=None):
        if model is self.db.Feedback:
            comment = item['comment']
            if len(comment) > 40:
                comment = comment[:40].strip() + '...'
            return ("<strong>'%s' feedback!</strong> %s"
                    % (item['what'], comment))

        if model is self.db.User:
            if locations is None:
                locations = {}
            if item['current_location'] not in locations:
                locations[item['current_location']] = \
                                 (self.db.Location
                                  .find_one({'_id': item['current_location']}))
            current_location = locations[item['current_location']]
            return ('<strong>User!</strong> %s (currently in %s)' %
                    (item['username'], current_location))

        if model is self.db.Question:
            if categories is None:
                categories = {}
            if item['category'] not in categories:
                categories[item['category']] = (self.db.Category
                                          .find_one({'_id': item['category']}))
            category = categories[item['category']]
            text = truncate_text(item['text'], 80)
            text = ("<strong>'%s' question!</strong> %s" %
                    (category['name'], text))
            if (self.db.QuestionPicture
                .find({'question': item['_id']})
                .count()):
                text += ' (with picture)'
            return text.strip()

        if model is self.db.HTMLDocument:
            text = "<strong>'%s' document!</strong> " % item['type']
            if item['user']:
                user = self.db.User.find_one({'_id': item['user']})
                text += 'about user %s ' % user
            if item['location']:
                location = self.db.Location.find_one({'_id': item['location']})
                text += 'about %s ' % location
            if item['category']:
                category = self.db.Category.find_one({'_id': item['category']})
                text += 'for %s ' % category

            return text.strip()

        if model is self.db.Award:
            user = self.db.User.find_one({'_id': item['user']})
            return (
                "%s earned the <strong>%s award</strong> "
                "with %s coins reward! "
                % (user['username'], item['type'], item['reward'])
            )

        raise NotImplementedError(model._obj_class)


@route('/admin/git.log', name='admin_git_log')
class GitLogHandler(AuthenticatedBaseHandler):

    @tornado.web.asynchronous
    def get(self):
        self.ioloop = tornado.ioloop.IOLoop.instance()
        cmd = ('git log master --date=iso '
               '--pretty=format:"%h%x09%an%x09%ad%x09%s"')
        self.pipe = p = os.popen(cmd)
        self.ioloop.add_handler(
            p.fileno(),
            self.async_callback(self.on_response),
            self.ioloop.READ
        )

    def on_response(self, fd, events):
        self.set_header('Content-Type', 'text/plain')
        for line in self.pipe:
            self.write(line)

        self.ioloop.remove_handler(fd)
        self.finish()


@route('/admin/jobs/', name='admin_jobs')
class JobsAdminHandler(AuthenticatedBaseHandler):

    LIMIT = 40

    def get(self):
        data = {}
        filter_ = {}
        data['all_locations'] = list(
            self.db.Location
            .find({'airport_name': {'$ne': None}})
            .sort('code')
        )
        data['all_categories'] = list(
            self.db.Category
            .find()
            .sort('name')
        )
        data['locations'] = self.get_arguments('locations', [])
        if data['locations']:
            filter_['location'] = {
                '$in': [x['_id'] for x in
                        self.db.Location
                        .find({'code': {'$in': data['locations']}})]
            }

        data['categories'] = self.get_arguments('categories', [])
        if data['categories']:
            filter_['category'] = {
                '$in': [x['_id'] for x in
                        self.db.Category
                        .find({'name': {'$in': data['categories']}})]
            }

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT

        jobs = []
        _locations = dict([(x['_id'], x) for x in data['all_locations']])
        _categories = dict([(x['_id'], x) for x in data['all_categories']])
        _users = {}
        data['count'] = self.db.Job.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)

        coins_all = []
        coins_categories = defaultdict(list)
        coins_locations = defaultdict(list)

        for each in (self.db.Job
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['user'] and each['user'] not in _users:
                _users[each['user']] = (
                    self.db.User.find_one({'_id': each['user']})
                )
            if each['location'] not in _locations:
                _locations[each['location']] = (
                    self.db.Location.find_one({'_id': each['location']})
                )

            jobs.append((
                each,
                _users[each['user']],
                _categories[each['category']],
                _locations[each['location']],
            ))

            category = _categories[each['category']]['name']
            coins_all.append(each['coins'])
            coins_categories[category].append(each['coins'])
            location = _locations[each['location']]['code']
            coins_locations[location].append(each['coins'])

        def median(seq):
            seq.sort()
            return seq[len(seq) / 2]

        data['coins_median'] = median(coins_all)
        data['coins_total'] = sum(coins_all)

        data['coins_categories'] = [(k, median(v), sum(v))
                                    for (k, v) in coins_categories.items()]
        data['coins_locations'] = [(k, median(v), sum(v))
                                   for (k, v) in coins_locations.items()]

        data['jobs'] = jobs
        data['filtering'] = bool(filter_)
        self.render('admin/jobs.html', **data)


@route('/admin/errors/', name='admin_errors')
class JobsAdminHandler(SuperuserBaseHandler):

    def get(self):
        data = {}
        filter_ = {}
        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT

        errors = []
        _users = {}
        data['count'] = self.db.ErrorEvent.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])

        data['filtering'] = bool(filter_)

        for each in (self.db.ErrorEvent
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['user']:
                if each['user'] not in _users:
                    _users[each['user']] = (
                        self.db.User.find_one({'_id': each['user']})
                    )
                user = _users[each['user']]
            else:
                user = None

            errors.append((
                each,
                user,
            ))

        data['errors'] = errors
        data['filtering'] = bool(filter_)
        self.render('admin/errors.html', **data)


@route('/admin/awards/?', name='admin_awards')
class AwardsAdminHandler(AuthenticatedBaseHandler):

    @tornado.web.addslash
    def get(self):
        data = {}
        filter_ = {}
        data['all_locations'] = list(
            self.db.Location
            .find({'airport_name': {'$ne': None}})
            .sort('code')
        )
        data['all_categories'] = list(
            self.db.Category
            .find()
            .sort('name')
        )
        from core import handlers
        data['all_types'] = (
            handlers.AWARDTYPE_JOB,
            handlers.AWARDTYPE_TUTORIAL,
            handlers.AWARDTYPE_SIGNIN,
            handlers.AWARDTYPE_10KMILES,
            handlers.AWARDTYPE_50KMILES,
            handlers.AWARDTYPE_100KMILES,
        )
        data['types'] = self.get_arguments('types', [])
        if data['types']:
            filter_['type'] = {
                '$in': data['types']
            }
        data['locations'] = self.get_arguments('locations', [])
        if data['locations']:
            filter_['location'] = {
                '$in': [x['_id'] for x in
                        self.db.Location
                        .find({'code': {'$in': data['locations']}})]
            }
        data['categories'] = self.get_arguments('categories', [])
        if data['categories']:
            filter_['category'] = {
                '$in': [x['_id'] for x in
                        self.db.Category
                        .find({'name': {'$in': data['categories']}})]
            }

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = (data['page'] - 1) * self.LIMIT

        awards = []
        _locations = dict([(x['_id'], x) for x in data['all_locations']])
        _categories = dict([(x['_id'], x) for x in data['all_categories']])
        _users = {}
        data['count'] = self.db.Award.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)

        for each in (self.db.Award
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['user'] and each['user'] not in _users:
                _users[each['user']] = (
                    self.db.User.find_one({'_id': each['user']})
                )
            if each['location'] not in _locations:
                _locations[each['location']] = (
                    self.db.Location.find_one({'_id': each['location']})
                )

            awards.append((
                each,
                _users[each['user']],
                each['category'] and _categories[each['category']] or None,
                _locations[each['location']],
            ))

        data['awards'] = awards
        data['filtering'] = bool(filter_)
        self.render('admin/awards.html', **data)
