import models
import settings


db = models.connection[settings.DATABASE_NAME]

def run(**options):
    def ensure(coll, arg):
        coll.ensure_index(arg,
                          background=options.get('background', False))
        return '%s.%s' % (coll.name, arg)

    collection = db.UserSettings.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')

    collection = db.Ambassador.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')

    test()


def test():
    any_obj_id = list(db.User.find().limit(1))[0]['_id']

    curs = db.UserSettings.find({'user': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs

    curs = db.Ambassador.find({'user': any_obj_id}).explain()['cursor']
    assert 'BtreeCursor' in curs
