import re
import urllib
import random
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from tornado_utils import timesince
from .forms import UserForm
from .base import djangolike_request_dict, SuperuserBaseHandler
from core.ui_modules import commafy


@route('/admin/users/', name='admin_users')
class UsersAdminHandler(SuperuserBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        data['q'] = self.get_argument('q', '')
        if data['q']:
            _q = [re.escape(x.strip()) for x in data['q'].split(',')
                  if x.strip()]
            filter_['username'] = re.compile('|'.join(_q), re.I)

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        users = []
        data['count'] = self.db.User.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)
        _locations = {}
        _ambassador_users = {}
        for each in self.db.Ambassador.find():
            _ambassador_users[each['user']] = each['country']
        for each in (self.db.User
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['current_location'] not in _locations:
                _locations[each['current_location']] = \
                  self.db.Location.find_one({'_id': each['current_location']})

            each.is_ambassador = _ambassador_users.get(each['_id'])
            users.append((
              each,
              self.db.UserSettings.find_one({'user': each['_id']}),
              _locations[each['current_location']],
              self.get_total_earned(each),
            ))
        data['users'] = users
        self.render('admin/users.html', **data)

@route('/admin/users/totals/', name='admin_users_totals')
class UsersTotalEarnedAdminHandler(SuperuserBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        totals = []
        data['count'] = self.db.TotalEarned.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)
        i = 0
        for each in (self.db.TotalEarned
                     .find(filter_)
                     .sort('coins', -1)
                     .limit(self.LIMIT)
                     .skip(skip)):
            i += 1
            user = self.db.User.collection.find_one({'_id': each['user']})
            totals.append((
              i + skip,
              each,
              user,
            ))
        data['no_users'] = self.db.User.find().count()
        data['no_totals'] = self.db.TotalEarned.find().count()
        if data['no_totals'] > data['no_users']:
            self._clean_unused_totals()
            data['no_users'] = self.db.User.find().count()
            data['no_totals'] = self.db.TotalEarned.find().count()

        data['totals'] = totals
        self.render('admin/users_totals.html', **data)

    def _clean_unused_totals(self):
        # this is slow but only happens very rarely
        for each in self.db.TotalEarned.collection.find(None, ('user',)):
            c = self.db.TotalEarned.find({'user': each['user']}).count()
            if c != 1:
                [x.delete() for x in self.db.TotalEarned.find({'user': each['user']})]
            elif not self.db.User.find({'_id': each['user']}).count():
                [x.delete() for x in self.db.TotalEarned.find({'user': each['user']})]

    def post(self):
        all_users = set([
          x['_id'] for x in
          self.db.User.collection.find(None, ('_id',))
        ])
        all_already = set([
          x['user'] for x in
          self.db.TotalEarned.collection.find(None, ('user',))
        ])
        remaining = list(all_users - all_already)
        random.shuffle(remaining)
        c = 0
        for user in self.db.User.collection.find({'_id': {'$in': remaining[:1000]}}):
            self.get_total_earned(user)
            c += 1

        self.push_flash_message(
            '%s users processed' % c,
            text='%s remaining' % (len(remaining) - c),
            type_='success'
        )

        self.redirect(self.reverse_url('admin_users_totals'))



@route('/admin/users/(\w{24})/', name='admin_user')
class UserAdminHandler(SuperuserBaseHandler):

    @property
    def countries(self):
        countries = (self.db.Location.find()
                     .distinct('country'))
        countries.sort()
        return countries

    def get(self, _id, form=None):
        data = {}
        user = self.db.User.find_one({'_id': ObjectId(_id)})
        data['user'] = user
        if form is None:
            initial = dict(user)
            initial['ambassador'] = [x['country'] for x in
                                     self.db.Ambassador
                                      .find({'user': user['_id']})]
            form = UserForm(countries=self.countries, **initial)
        data['form'] = form
        data['user_settings'] = (self.db.UserSettings
                                 .find_one({'user': user['_id']}))
        data['total_earned'] = self.get_total_earned(user)
        data['current_location'] = (self.db.Location
                                 .find_one({'_id': user['current_location']}))
        data['count_friendships'] = (self.db.Friendship
                                     .find({'user': user['_id']})
                                     .count())
        data['count_mutual_friendships'] = (self.db.Friendship
                                            .find({'user': user['_id'],
                                                   'mutual': True})
                                            .count())
        self.render('admin/user.html', **data)

    def post(self, _id):
        data = {}
        user = self.db.User.find_one({'_id': ObjectId(_id)})
        data['user'] = user
        post_data = djangolike_request_dict(self.request.arguments)

        form = UserForm(post_data, countries=self.countries)
        if form.validate():
            user['username'] = form.username.data
            user['email'] = form.email.data
            user['first_name'] = form.first_name.data
            user['last_name'] = form.last_name.data
            user['superuser'] = form.superuser.data
            user.save()

            countries = form.ambassador.data
            for each in self.db.Ambassador.find({'user': user['_id']}):
                if each['country'] not in countries:
                    each.delete()
                else:
                    countries.remove(each['country'])
            for country in countries:
                ambassador = self.db.Ambassador()
                ambassador['user'] = user['_id']
                ambassador['country'] = country
                ambassador.save()

            self.redirect(self.reverse_url('admin_users'))
        else:
            self.get(_id, form=form)


@route('/admin/users/(\w{24})/journey/', name='admin_user_journey')
class UserJourneyAdminHandler(UserAdminHandler):

    def get(self, _id, form=None):
        data = {}
        user = self.db.User.find_one({'_id': ObjectId(_id)})
        events = []
        _categories = {}
        _locations = {}

        for job in (self.db.Job.find({'user': user['_id']})
                    .sort('add_date', -1)):
            if job['category'] not in _categories:
                _categories[job['category']] = \
                  self.db.Category.find_one({'_id': job['category']})
            if job['location'] not in _locations:
                _locations[job['location']] = \
                  self.db.Location.find_one({'_id': job['location']})
            category = _categories[job['category']]
            location = _locations[job['location']]
            description = ("Completed %s and earned %s coins" %
                           (category, job['coins']))
            events.append((
              job['add_date'],
              description,
              location,
              'job',
            ))

        for flight in (self.db.Flight.find({'user': user['_id']})
                      .sort('add_date', -1)):
            if flight['from'] not in _locations:
                _locations[flight['from']] = \
                  self.db.Location.find_one({'_id': flight['from']})
            if flight['to'] not in _locations:
                _locations[flight['to']] = \
                  self.db.Location.find_one({'_id': flight['to']})
            from_ = _locations[flight['from']]
            to = _locations[flight['to']]
            description = ("Flew %s miles from %s to %s" %
                           (commafy(int(flight['miles'])),
                            from_, to))
            events.append((
              flight['add_date'],
              description,
              from_,
              'flight',
            ))

        for award in (self.db.Award.find({'user': user['_id']})
                      .sort('add_date', -1)):
            location = '--'
            if award['location']:
                if award['location'] not in _locations:
                    _locations[award['location']] = \
                      self.db.Location.find_one({'_id': award['location']})
                location = _locations[award['location']]
            description = (
              "%s award earning %s coins reward"
              % (award['type'], award['reward'])
            )
            events.append((
              award['add_date'],
              description,
              location,
              'award',
            ))

        for msg in (self.db.LocationMessage.find({'user': user['_id']})
                      .sort('add_date', -1)):
            if msg['location'] not in _locations:
                _locations[msg['location']] = \
                  self.db.Location.find_one({'_id': msg['location']})
            location = _locations[msg['location']]
            description = "Wrote a message!"
            if msg['censored']:
                description += " (censored)"
            brief = msg['message']
            if len(brief) > 40:
                brief = brief[:40] + '...'
            description += " '%s'" % brief
            events.append((
              msg['add_date'],
              description,
              location,
              'message',
            ))

        for feedback in (self.db.Feedback.find({'user': user['_id']})
                        .sort('add_date', -1)):
            if feedback['location'] not in _locations:
                _locations[feedback['location']] = \
                  self.db.Location.find_one({'_id': feedback['location']})
            location = _locations[feedback['location']]
            description = "Wrote feedback!"
            brief = feedback['comment']
            if len(brief) > 40:
                brief = brief[:40] + '...'
            description += " '%s'" % brief
            events.append((
              feedback['add_date'],
              description,
              location,
              'feedback',
            ))

        for friendship in (self.db.Friendship.collection
                           .find({'user': user['_id']})
                           .sort('add_date', -1)):
            to = self.db.User.collection.find_one({'_id': friendship['to']})
            description = "Connected to %s" % self.get_name(to)
            if friendship['mutual']:
                description += ' (mutual)'
            events.append((
              friendship['add_date'],
              description,
              None,
              'friendship',
            ))

        events.sort()

        data['events'] = events
        data['user'] = user
        self.render('admin/user_journey.html', **data)


@route('/admin/users/(\w{24})/total/', name='admin_user_total')
class UserTotalEarnedAdminHandler(UserAdminHandler):

    def get(self, _id):
        data = {}
        user = self.db.User.find_one({'_id': ObjectId(_id)})
        total = self.get_total_earned(user)
        data['no_users'] = self.db.User.find().count()
        data['no_totals'] = self.db.TotalEarned.find().count()
        data['rank'] = self.db.TotalEarned.find({'coins': {'$gt': total['coins']}}).count() + 1
        data['total'] = total
        data['user'] = user
        self.render('admin/user_total.html', **data)
