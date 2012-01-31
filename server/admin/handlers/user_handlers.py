import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
#from .forms import UserForm
#from geopy import geocoders
from .base import SuperuserBaseHandler



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


@route('/admin/user/(\w{24})/', name='admin_user')
class UserAdminHandler(SuperuserBaseHandler):

    def get(self, _id, form=None):
        raise NotImplementedError
        data = {}
        data['location'] = self.db.Location.find_one({'_id': ObjectId(_id)})
        if form is None:
            initial = dict(data['location'])
            form = LocationForm(**initial)
        data['form'] = form
        self.render('admin/location.html', **data)

    def post(self, _id):
        raise NotImplementedError
        data = {}
        location = self.db.Location.find_one({'_id': ObjectId(_id)})
        data['location'] = location
        post_data = djangolike_request_dict(self.request.arguments)
        #if 'alternatives' in post_data:
        #    post_data['alternatives'] = ['\n'.join(post_data['alternatives'])]

        form = LocationForm(post_data)
        if form.validate():
            location['city'] = form.city.data
            location['country'] = form.country.data
            location['locality'] = form.locality.data or None
            location['code'] = form.code.data or None
            location['airport_name'] = form.airport_name.data or None
            location['lat'] = float(form.lat.data)
            location['lng'] = float(form.lng.data)
            location.save()
            self.redirect(self.reverse_url('admin_locations'))
        else:
            self.get(_id, form=form)
