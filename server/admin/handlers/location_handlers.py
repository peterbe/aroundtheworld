import mimetypes
import re
import urllib
from pymongo.objectid import ObjectId
from tornado_utils.routes import route
from .forms import LocationForm, LocationPictureForm
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

class BaseLocationPictureHandler(AmbassadorBaseHandler):

    @property
    def locations(self):
        user = self.get_current_user()
        filter_ = {'airport_name': {'$ne': None}}
        if not user['superuser']:
            countries = (self.db.Ambassador
                         .find({'user': user['_id']})
                         .distinct('country'))
            assert countries  # no support for mayors yet
            filter_['country'] = {'$in': countries}
        return (self.db.Location
                .find(filter_)
                .sort('code', 1))

@route('/admin/locations/pictures/', name='admin_location_pictures')
class LocationPicturesAdminHandler(AmbassadorBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        data['q'] = self.get_argument('q', '')
        if data['q']:
            _q = [re.escape(x.strip()) for x in data['q'].split(',')
                  if x.strip()]
            filter_['title'] = re.compile('|'.join(_q), re.I)
        data['all_locations'] = (
          self.db.Location
          .find({'airport_name': {'$ne': None}})
          .sort('code')
        )
        data['locations'] = self.get_arguments('locations', [])
        if data['locations']:
            filter_['location'] = {
              '$in': [x['_id'] for x in
                       self.db.Location
                        .find({'code': {'$in': data['locations']}})]
            }

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        pictures = []
        data['count'] = self.db.LocationPicture.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        data['filtering'] = bool(filter_)
        _locations = {}
        for each in (self.db.LocationPicture
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})

            pictures.append((
              each,
              _locations[each['location']],
            ))
        data['pictures'] = pictures
        self.render('admin/location_pictures.html', **data)



@route('/admin/locations/pictures/add/', name='admin_add_location_picture')
class AddLocationPictureAdminHandler(BaseLocationPictureHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            form = LocationPictureForm(locations=self.locations,
                                       picture_required=True)
        data['form'] = form
        self.render('admin/add_location_picture.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        if self.request.files:
            post_data.update(djangolike_request_dict(self.request.files))
        form = LocationPictureForm(post_data, locations=self.locations,
                                   picture_required=True)
        if form.validate():
            picture = self.db.LocationPicture()
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            picture['location'] = location['_id']
            picture['title'] = form.title.data
            picture['description'] = form.description.data
            if form.copyright.data:
                picture['copyright'] = form.copyright.data
            if form.copyright_url.data:
                if not form.copyright_url.data.count('://'):
                    form.copyright_url.data = 'http://' + form.copyright_url.data
                picture['copyright_url'] = form.copyright_url.data
            if form.notes.data:
                picture['notes'] = form.notes.data
            if not form.index.data:
                highest = 1
                for each in (self.db.LocationPicture
                             .find({'location': location['_id']})
                             .sort('index')
                             .limit(1)):
                    highest = each['index'] + 1
                picture['index'] = highest
            else:
                picture['index'] = int(form.index.data)
            picture.save()

            try:
                ok = False
                image = form.picture.data
                if not any([image['filename'].lower().endswith(x)
                            for x in ('.png', '.jpg', '.jpeg')]):
                    raise HTTPError(400)
                assert isinstance(image['body'], str), type(image['body'])
                type_, __ = mimetypes.guess_type(image['filename'])
                with picture.fs.new_file('original') as f:
                    f.content_type = type_
                    f.write(image['body'])
                ok = True
            finally:
                if not ok:
                    picture.delete()
                    self.push_flash_message(
                      'Picture upload failed',
                      text='Check that the requirements for the picture '
                           'is correct',
                      type_='error'
                      )

            self.redirect(self.reverse_url('admin_locations'))
        else:
            self.get(form=form)


@route('/admin/locations/pictures/(\w{24})/', name='admin_location_picture')
class LocationPictureAdminHandler(BaseLocationPictureHandler):

    def get(self, _id, form=None):
        data = {}
        data['location_picture'] = (self.db.LocationPicture
                                    .find_one({'_id': ObjectId(_id)}))
        if not data['location_picture']:
            raise HTTPError(404)
        if form is None:
            initial = dict(data['location_picture'])
            initial['location'] = str(initial['location'])
            form = LocationPictureForm(locations=self.locations,
                                       **initial)
        data['form'] = form
        self.render('admin/location_picture.html', **data)

    def post(self, _id):
        data = {}
        picture = self.db.LocationPicture.find_one({'_id': ObjectId(_id)})
        #data['location_picture'] = picture
        post_data = djangolike_request_dict(self.request.arguments)
        if self.request.files:
            post_data.update(djangolike_request_dict(self.request.files))
        form = LocationPictureForm(post_data,
                                   locations=self.locations)
        if form.validate():
            picture['title'] = form.title.data
            picture['description'] = form.description.data
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            picture['location'] = location['_id']
            if form.copyright.data:
                picture['copyright'] = form.copyright.data
            if form.copyright_url.data:
                if not form.copyright_url.data.count('://'):
                    form.copyright_url.data = 'http://' + form.copyright_url.data
                picture['copyright_url'] = form.copyright_url.data
            if form.notes.data:
                picture['notes'] = form.notes.data
            if form.index.data:
                picture['index'] = int(form.index.data)

            if form.picture.data:
                ok = False
                image = form.picture.data
                if not any([image['filename'].lower().endswith(x)
                            for x in ('.png', '.jpg', '.gif', '.jpeg')]):
                    raise HTTPError(400)
                assert isinstance(image['body'], str), type(image['body'])
                type_, __ = mimetypes.guess_type(image['filename'])
                with picture.fs.new_file('original') as f:
                    f.content_type = type_
                    f.write(image['body'])
                ok = True

            picture.save()
            self.redirect(self.reverse_url('admin_location_pictures'))
        else:
            self.get(_id, form=form)
