from wtforms import (Form, BooleanField, TextField, TextAreaField, validators,
                     SelectField)
from wtforms.widgets import html_params, TextInput
from wtforms.validators import ValidationError


class BaseForm(Form):
    def validate(self, *args, **kwargs):
        for name, f in self._fields.iteritems():
            if isinstance(f.data, str):
                f.data = unicode(f.data, 'utf-8')
            if isinstance(f.data, basestring):
                f.data = f.data.strip()
        return super(BaseForm, self).validate(*args, **kwargs)


class TextInputWithMaxlength(TextInput):
    def __init__(self, maxlength, *args, **kwargs):
        self.maxlength = maxlength
        self.attrs = kwargs.pop('attrs', {})
        super(TextInputWithMaxlength, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        kwargs.update(dict(maxlength=self.maxlength))
        kwargs.update(self.attrs)
        return super(TextInputWithMaxlength, self).__call__(*args, **kwargs)


class MultilinesWidget(object):
    def __init__(self, length=4, vertical=False):
        self.length = length
        self.vertical = vertical

    def __call__(self, field, **kwargs):
        kwargs.setdefault('id', field.id)
        htmls = []

        value = field.data
        if isinstance(value, basestring):
            values = [x.strip() for x in value.splitlines() if x.strip()]
        else:
            values = value
        #print "__call__ values", repr(values)
        _removed_title = False
        for i in range(self.length):
            if values is None:
                value = u''
            else:
                try:
                    value = values[i]
                except IndexError:
                    value = u''
            kwargs['value'] = value
            kwargs_copy = dict(kwargs, id='%s_%s' % (kwargs['id'], i))
            html = '<input %s />' % html_params(name=field.name, **kwargs_copy)
            if not _removed_title:
                if 'title' in kwargs:
                    kwargs.pop('title')
                _removed_title = True
            htmls.append(html)
            if self.vertical:
                htmls.append('<br/>')
        return '\n'.join(htmls)


class QuestionForm(BaseForm):
    text = TextField("Question",
                     [validators.Required(),
                      validators.Length(min=5, max=100)],
                     description="Make sure the question ends with a ?",
                     widget=TextInputWithMaxlength(100, attrs={
                       'size': 100,
                       'class': 'xlarge',
                     }),
                     id="id_text")
    correct = TextField("Answer",
                       [validators.Required(),
                        validators.Length(min=1, max=50)],
                      description="Make it reasonably short and easy to type",
                      widget=TextInputWithMaxlength(50),
                      id="id_correct")
    alternatives = TextAreaField("Alternatives",
                                 [validators.Required()],
                                 description='',
                                 widget=MultilinesWidget(length=4,
                                                         vertical=True))
    alternatives_sorted = BooleanField("Alternatives ordered",
                                 description="Bla bla")
    points_value = SelectField("Points value",
                               choices=[(str(x), str(x)) for x
                                        in range(1, 5 + 1)])
    published = BooleanField("Published")
    category = SelectField("Category",
                      [validators.Required()])
    location = SelectField("City",
                      [validators.Required()])
    notes = TextAreaField("Notes",
                            description="Any references or links to "\
                                        "strengthen your answer")

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        self.category.choices = [
          (str(x['_id']), x['name'])
          for x in kwargs['categories']
        ]
        self.location.choices = [
          (str(x['_id']), '%s (%s)' % (x['code'], x['country']))
          for x in kwargs['locations']
        ]

    def validate(self, *args, **kwargs):
        success = super(QuestionForm, self).validate(*args, **kwargs)
        if success:
            # check invariants
            if self.data['correct'] not in self.data['alternatives'].split():
                (self._fields['correct']
                  .errors.append("Answer not in alternatives"))
                success = False
        return success


class Floatable(object):

    def __call__(self, form, field):
        if field.data:
            try:
                float(field.data)
            except ValueError:
                raise ValidationError("Not a floating point number")


class LocationForm(BaseForm):
    city = TextField("City",
                     [validators.Required(),
                      validators.Length(min=1, max=40)])
    country = TextField("Country",
                     [validators.Required(),
                      validators.Length(min=1, max=40)])
    locality = TextField("Locality")
    code = TextField("Airport code",
                     [validators.Optional(),
                      validators.Length(min=3, max=3)])
    airport_name = TextField("Airport name",
                     [validators.Optional(),
                      validators.Length(min=3, max=100)])
    lat = TextField("Latitude", [validators.Required(), Floatable()])
    lng = TextField("Longitude", [validators.Required(), Floatable()])
