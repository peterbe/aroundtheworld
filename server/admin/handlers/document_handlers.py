import re
import urllib
from bson.objectid import ObjectId
from tornado_utils.routes import route
from .forms import DocumentForm, AddDocumentForm
from .base import djangolike_request_dict, AmbassadorBaseHandler


@route('/admin/documents/', name='admin_documents')
class DocumentsAdminHandler(AmbassadorBaseHandler):
    LIMIT = 20

    def get(self):
        data = {}
        filter_ = {}
        #data['q_city'] = self.get_argument('q_city', '')
        #if data['q_city']:
        #    filter_['city'] = re.compile(
        #      '^%s' % re.escape(data['q_city']), re.I)
        #data['q_locality'] = self.get_argument('q_locality', '')
        #if data['q_locality']:
        #    filter_['locality'] = re.compile(
        #      '^%s' % re.escape(data['q_locality']), re.I)
        data['all_types'] = (self.db.HTMLDocument
                             .find()
                             .distinct('type'))
        data['all_types'].sort()
        data['types'] = self.get_arguments('types', [])
        if data['types']:
            filter_['type'] = {'$in': data['types']}
        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        documents = []
        data['count'] = self.db.HTMLDocument.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        data['filtering'] = bool(filter_)
        _users = {}
        _locations = {}
        _categories = {}
        for each in (self.db.HTMLDocument
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):

            if each['location'] and each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})
            if each['user'] and each['user'] not in _users:
                _users[each['user']] = \
                  self.db.User.find_one({'_id': each['user']})
            try:each['category']
            except KeyError:
                each['category'] = None
                each.save()
            if each['category'] and each['category'] not in _categories:
                _categories[each['category']] = \
                  self.db.Category.find_one({'_id': each['category']})
            documents.append((
              each,
              each['location'] and _locations[each['location']] or None,
              each['user'] and _users[each['user']] or None,
              each['category'] and _categories[each['category']] or None,
            ))
        data['documents'] = documents
        self.render('admin/documents.html', **data)


@route('/admin/documents/(\w{24})/', name='admin_document')
class DocumentAdminHandler(AmbassadorBaseHandler):

    def get(self, _id, form=None):
        data = {}
        document = self.db.HTMLDocument.find_one({'_id': ObjectId(_id)})
        data['user'] = None
        data['location'] = None
        data['category'] = None
        if document['location']:
            data['location'] = (self.db.Location
                                .find_one({'_id': document['location']}))
        if document['user']:
            data['user'] = self.db.User.find_one({'_id': document['user']})
        if document['category']:
            data['category'] = (self.db.Category
                                .find_one({'_id': document['category']}))

        if form is None:
            initial = dict(document)
            form = DocumentForm(**initial)
        data['form'] = form
        data['document'] = document
        self.render('admin/document.html', **data)

    def post(self, _id):
        data = {}
        document = self.db.HTMLDocument.find_one({'_id': ObjectId(_id)})
        data['document'] = document
        post_data = djangolike_request_dict(self.request.arguments)
        #if 'alternatives' in post_data:
        #    post_data['alternatives'] = ['\n'.join(post_data['alternatives'])]

        form = DocumentForm(post_data)
        if form.validate():
            document['source'] = form.source.data
            document['source_format'] = form.source_format.data
            document['type'] = form.type.data
            document['notes'] = form.notes.data
            document.update_html()  # calls self.save()
            self.redirect(self.reverse_url('admin_documents'))
        else:
            self.get(_id, form=form)


@route('/admin/documents/add/', name='admin_add_document')
class AddDocumentAdminHandler(AmbassadorBaseHandler):

    def find_locations(self, search):
        locations = []
        _code = re.findall('^([A-Z]{3})\s', search)
        if _code:
            return [self.db.Location.find_one({'code': _code[0]})]
        for each in ('city', 'code'):
            regex = re.compile('^%s' % re.escape(search), re.I)
            filter_ = {
              each: regex,
              'airport_name': {'$ne': None}
            }
            if locations:
                filter_['_id'] = {'$nin': [x['_id'] for x in locations]}
            for location in self.db.Location.find(filter_):
                locations.append(location)
        return locations

    def find_users(self, search):
        users = []
        for each in ('username', 'email', 'first_name', 'last_name'):
            regex = re.compile('^%s' % re.escape(search), re.I)
            filter_ = {
              each: regex,
            }
            if users:
                filter_['_id'] = {'$nin': [x['_id'] for x in users]}
            for user in self.db.User.find(filter_):
                users.append(user)
        return users

    def find_categories(self, search):
        categories = []
        regex = re.compile('^%s' % re.escape(search), re.I)
        for category in self.db.Category.find({'name': regex}).sort('name'):
            categories.append(category)
        return categories

    def get(self, form=None):
        data = {}
        if form is None:
            form = AddDocumentForm()
        data['form'] = form
        self.render('admin/add_document.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        form = AddDocumentForm(post_data)
        if form.validate():
            document = self.db.HTMLDocument()
            document['source'] = form.source.data
            document['source_format'] = form.source_format.data
            document['notes'] = form.notes.data
            if form.location.data:
                location = self.find_locations(form.location.data)[0]
                document['location'] = location['_id']
            if form.user.data:
                user = self.find_users(form.user.data)[0]
                document['user'] = user['_id']
            if form.category.data:
                category = self.find_categories(form.category.data)[0]
                document['category'] = category['_id']
            document['type'] = form.type.data
            document.save()

            self.redirect(self.reverse_url('admin_document',
                                           str(document['_id'])))
        else:
            self.get(form=form)


@route('/admin/findlocation.json')
class FindLocationAdminHandler(AddDocumentAdminHandler):

    def get(self):
        search = self.get_argument('location')
        locations = self.find_locations(search)
        results = ['%s %s' % (x['code'], x) for x in locations]
        self.write({'results': results})


@route('/admin/finduser.json')
class FindUserAdminHandler(AddDocumentAdminHandler):

    def get(self):
        search = self.get_argument('user')
        users = self.find_users(search)
        results = []
        for user in users:
            r = user['username']
            if user['first_name'] and user['last_name']:
                r += ', %s %s' % (user['first_name'], user['last_name'])
            if user['email']:
                r += ', %s' % user['email']
            results.append(r)
        self.write({'results': results})


@route('/admin/findcategory.json')
class FindCategoryAdminHandler(AddDocumentAdminHandler):

    def get(self):
        search = self.get_argument('category')
        categories = self.find_categories(search)
        results = []
        for category in categories:
            results.append(category['name'])
        self.write({'results': results})
