import tornado.web
import tornado.escape
from admin.utils import truncate_text

class RenderField(tornado.web.UIModule):
    def render(self, field):
        try:
            return field(title=field.description)
        except TypeError:
            return field()


class ShowComment(tornado.web.UIModule):

    def render(self, comment):
        return tornado.escape.linkify(comment).replace('\n', '<br>\n')


class Truncate(tornado.web.UIModule):

    def render(self, text, characters):
        return tornado.escape.xhtml_escape(truncate_text(text, characters))


class SortArrow(tornado.web.UIModule):

    def render(self, key, sort_key, sort_order):
        return self.render_string("admin/_sort_arrow.html",
                                  key=key,
                                  sort_key=sort_key,
                                  sort_order=sort_order)
