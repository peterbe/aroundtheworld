import tornado.web


def _commafy(s):
    r = []
    for i, c in enumerate(reversed(str(s))):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    return ''.join(r)


class Thousands(tornado.web.UIModule):

    def render(self, number):
        return _commafy(str(number))


class JSON(tornado.web.UIModule):

    def render(self, data):
        return tornado.escape.json_encode(data)
