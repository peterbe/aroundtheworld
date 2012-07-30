import datetime
import mimetypes
import re
import urllib
from pymongo.objectid import ObjectId
from tornado.web import HTTPError
from tornado_utils.routes import route
from .forms import BankForm
from geopy import geocoders
from .base import djangolike_request_dict, SuperuserBaseHandler


class BanksBaseHandler(SuperuserBaseHandler):

    @property
    def locations_with_airports(self):
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



@route('/admin/banks/', name='admin_banks')
class BanksAdminHandler(BanksBaseHandler):

    def get(self):
        data = {}
        filter_ = {}
        data['q_city'] = self.get_argument('q_city', '')
        if data['q_city']:
            filter_['city'] = re.compile(
              '^%s' % re.escape(data['q_city']), re.I)

#        data['available'] = self.get_argument('available', '')
#        if data['available']:
#            # temporary legacy fix
#            for x in self.db.Location.find({'available': {'$exists': False}}):
#                x['available'] = False
#                x.save()
#
#            filter_['available'] = _bool(data['available'])

        args = dict(self.request.arguments)
        if 'page' in args:
            args.pop('page')
        data['query_string'] = urllib.urlencode(args, True)

        data['page'] = int(self.get_argument('page', 1))
        skip = max(0, data['page'] - 1) * self.LIMIT
        banks = []
        data['count'] = self.db.Bank.find(filter_).count()
        data['all_pages'] = range(1, data['count'] / self.LIMIT + 2)
        self.trim_all_pages(data['all_pages'], data['page'])
        data['filtering'] = bool(filter_)
        _locations = {}
        for each in (self.db.Bank
                     .find(filter_)
                     .sort('add_date', -1)  # newest first
                     .limit(self.LIMIT)
                     .skip(skip)):
            if each['location'] not in _locations:
                _locations[each['location']] = \
                  self.db.Location.find_one({'_id': each['location']})
            sum_deposits = sum(x['amount'] for x in
                               self.db.Deposit.collection
                               .find({'bank': each['_id']}, ('amount',)))
            banks.append((
                each,
                _locations[each['location']],
                sum_deposits
            ))
        data['banks'] = banks
        self.render('admin/banks/index.html', **data)

@route('/admin/banks/(\w{24})/', name='admin_bank')
class BankAdminHandler(BanksBaseHandler):

    def get(self, _id, form=None):
        data = {}
        data['bank'] = (self.db.Bank
                        .find_one({'_id': ObjectId(_id)}))
        if not data['bank']:
            raise HTTPError(404)
        if form is None:
            initial = dict(data['bank'])
            initial['location'] = str(initial['location'])
            form = BankForm(locations=self.locations_with_airports,
                            **initial)
        data['form'] = form
        self.render('admin/banks/edit.html', **data)

    def post(self, _id):
        data = {}
        bank = self.db.Bank.find_one({'_id': ObjectId(_id)})
        post_data = djangolike_request_dict(self.request.arguments)
        if self.request.files:
            post_data.update(djangolike_request_dict(self.request.files))
        form = BankForm(post_data,
                        locations=self.locations_with_airports)
        if form.validate():
            bank['name'] = form.name.data
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            bank['location'] = location['_id']
            bank['default_interest_rate'] = float(form.default_interest_rate.data)
            bank['open'] = form.open.data
            bank['withdrawal_fee'] = form.withdrawal_fee.data
            bank['deposit_fee'] = form.deposit_fee.data
            bank.save()
            self.push_flash_message(
                'Bank saved',
                "Details for '%s' details saved." % bank['name']
            )
            self.redirect(self.reverse_url('admin_banks'))
        else:
            self.get(_id, form=form)


@route('/admin/banks/add/', name='admin_add_bank')
class AddBankAdminHandler(BanksBaseHandler):

    def get(self, form=None):
        data = {}
        if form is None:
            form = BankForm(locations=self.locations_with_airports)
        data['form'] = form
        self.render('admin/banks/add.html', **data)

    def post(self):
        post_data = djangolike_request_dict(self.request.arguments)
        form = BankForm(post_data, locations=self.locations_with_airports)
        if form.validate():
            bank = self.db.Bank()
            bank['name'] = form.name.data
            location = (self.db.Location
                        .find_one({'_id': ObjectId(form.location.data)}))
            assert location
            bank['location'] = location['_id']
            bank['default_interest_rate'] = float(form.default_interest_rate.data)
            bank['open'] = form.open.data
            bank['withdrawal_fee'] = form.withdrawal_fee.data or 0
            bank['deposit_fee'] = form.deposit_fee.data or 0
            bank.save()
            self.push_flash_message(
                'Bank added',
                "New bank called %s added" % bank['name']
            )
            self.redirect(self.reverse_url('admin_banks'))
        else:
            self.get(form=form)
