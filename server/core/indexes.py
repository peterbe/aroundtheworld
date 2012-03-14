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

    collection = db.QuestionSession.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')
    yield ensure(collection, 'location')
    yield ensure(collection, 'finish_date')

    collection = db.SessionAnswer.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'session')

    collection = db.PinpointAnswer.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'session')

    collection = db.PinpointSession.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')
    yield ensure(collection, 'center')

    collection = db.Transaction.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')

    collection = db.QuestionAnswerEarning.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')

    collection = db.Flight.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')

    collection = db.Job.collection
    if options.get('clear_all_first'):
        collection.drop_indexes()
    yield ensure(collection, 'user')
    yield ensure(collection, 'category')
    yield ensure(collection, 'location')

    collection = db.Award.collection
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
