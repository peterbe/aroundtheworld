import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from .forms import LocationForm
from geopy import geocoders
from .base import djangolike_request_dict, AmbassadorBaseHandler


@route('/admin/locations/', name='admin_locations')
class LocationsAdminHandler(AmbassadorBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        data['q_city'] = self.get_argument('q_city', '')
        if data['q_city']:
            filter_['city'] = re.compile(
              '^%s' % re.escape(data['q_city']), re.I)
        data['q_locality'] = self.get_argument('q_locality', '')
        if data['q_locality']:
            filter_['locality'] = re.compile(
              '^%s' % re.escape(data['q_locality']), re.I)
        data['all_countries'] = (self.db.Location
                                 .find()
                                 .distinct('country'))
        data['all_countries'].sort()
        data['countries'] = self.get_arguments('countries', [])
        if data['countries']:
            filter_['country'] = {'$in': data['countries']}

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        locations = []
        data['count'] = self.db.Location.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        data['filtering'] = bool(filter_)
        for each in (self.db.Location
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            locations.append(each)
        data['locations'] = locations
        self.render('admin/locations.html', **data)


@route('/admin/locations/(\w{24})/', name='admin_location')
class LocationAdminHandler(AmbassadorBaseHandler):

    def get(self, _id, form=None):
        data = {}
        data['location'] = self.db.Location.find_one({'_id': ObjectId(_id)})
        if form is None:
            initial = dict(data['location'])
            form = LocationForm(**initial)
        data['form'] = form
        self.render('admin/location.html', **data)

    def post(self, _id):
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


@route('/admin/geocode.json')
class GeocodeAdminHandler(AmbassadorBaseHandler):

    def get(self):
        city = self.get_argument('city')
        country = self.get_argument('country')
        locality = self.get_argument('locality', '')
        search = [city]
        if locality:
            search.append(locality)
        search.append(country)
        search = ', '.join(search)

        g = geocoders.Google()
        results = []
        for place, (lat, lng) in g.geocode(search, exactly_one=False):
            results.append({
              'place': place,
              'lat': lat,
              'lng': lng,
            })
        self.write_json({'results': results})
        return


@route('/admin/locations/add/', name='admin_add_location')
class AddLocationAdminHandler(AmbassadorBaseHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            form = LocationForm()
        data['form'] = form
        self.render('admin/add_location.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        form = LocationForm(post_data)
        if form.validate():
            location = self.db.Location()
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
            self.get(form=form)
