import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from .forms import UserForm
from .base import djangolike_request_dict, SuperuserBaseHandler


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
        #data['q_city'] = self.get_argument('q_city', '')
        #if data['q_city']:
        #    filter_['city'] = re.compile(
        #      '^%s' % re.escape(data['q_city']), re.I)
        #data['q_locality'] = self.get_argument('q_locality', '')
        #if data['q_locality']:
        #    filter_['locality'] = re.compile(
        #      '^%s' % re.escape(data['q_locality']), re.I)
        #data['all_countries'] = (self.db.Location
        #                         .find()
        #                         .distinct('country'))
        #data['all_countries'].sort()
        #data['countries'] = self.get_arguments('countries', [])

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        users = []
        data['count'] = self.db.User.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
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
              _locations[each['current_location']]
            ))
        data['users'] = users
        self.render('admin/users.html', **data)


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
        data['current_location'] = (self.db.Location
                                 .find_one({'_id': user['current_location']}))
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
