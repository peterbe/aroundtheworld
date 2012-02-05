import tornado.web
import tornado.escape

class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()


class ShowComment(tornado.web.UIModule):
    def render(self, comment):
        return tornado.escape.linkify(comment).replace('\n','<br>\n')
