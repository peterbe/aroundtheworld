from wtforms import (Form, BooleanField, TextField, TextAreaField, validators,
                     SelectField, SelectMultipleField, FileField)
from wtforms.widgets import html_params, TextInput, TextArea as WTTextArea
from wtforms.validators import ValidationError

class TextArea(WTTextArea):
    def __init__(self, **attrs):
        self.attrs = attrs

    def __call__(self, field, **kwargs):
        self.attrs.update(kwargs)
        return super(TextArea, self).__call__(field, **self.attrs)


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


class SecondsValidator(object):

    def __init__(self, min_, max_):
        self.min_ = min_
        self.max_ = max_

    def __call__(self, form, field):
        if field.data:
            if int(field.data) < self.min_:
                raise ValidationError("Must be at least %s" % self.min_)
            if int(field.data) > self.max_:
                raise ValidationError("Must be at max %s" % self.max_)


class CategoryForm(BaseForm):
    name = TextField("Category",
                    [validators.Required(),
                     validators.Length(min=2, max=100)],
                    widget=TextInputWithMaxlength(100, attrs={
                      'size': 100,
                      'class': 'xlarge',
                    }))
    manmade = BooleanField("Man made", description="Manually created")

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.categories = kwargs['categories']
        self.category = kwargs.get('category', None)

    def validate(self, *args, **kwargs):
        success = super(CategoryForm, self).validate(*args, **kwargs)
        if success:
            names = [x['name'].lower() for x in self.categories]
            if self.category:
                if self.category['name'].lower() in names:
                    names.remove(self.category['name'].lower())
            if self.data['name'].lower() in names:
                self._fields['name'].errors.append(
                  "Category already exists"
                )
                success = False
        return success


class QuestionForm(BaseForm):
    text = TextField("Question",
                     [validators.Required(),
                      validators.Length(min=5, max=200)],
                     description="Make sure the question ends with a ?",
                     widget=TextInputWithMaxlength(200, attrs={
                       'size': 200,
                       'class': 'span5',
                     }),
                     id="id_text")
    correct = TextField("Answer",
                       [validators.Required(),
                        validators.Length(min=1, max=100)],
                      description="Make it reasonably short and easy to type",
                      widget=TextInputWithMaxlength(100),
                      id="id_correct")
    alternatives = TextAreaField("Alternatives",
                                 [validators.Required()],
                                 description='',
                                 widget=MultilinesWidget(length=4,
                                                         vertical=True))
    alternatives_sorted = BooleanField("Alternatives ordered",
          description="Whether or not the alternatives should appear exactly "
                      "in this order when shown")

    picture = FileField("Picture (JPG or PNG)",
                        description="Optional picture to go with the question")

    points_value = SelectField("Points value",
          choices=[('1', '1 (easy)'),
                   ('2', '2'),
                   ('3', '3'),
                   ('4', '4'),
                   ('5', '5 (hard)')])

    seconds = TextField("Seconds",
                        [validators.Required(), SecondsValidator(10, 30)],
                        description="Number of seconds to think (min. 10, max. 30)"
                        )

    published = BooleanField("Published",
                    description="Whether it should immediately appear")
    category = SelectField("Category",
                      [validators.Required()])
    location = SelectField("City",
                      [validators.Required()])
    didyouknow = TextAreaField("Did you know...",
                     description="Some cute little extra fact that might brighten your day",
                     widget=TextArea(**{'class': 'span5'})
                     )
    notes = TextAreaField("Notes",
                          description="Any references or links to "\
                                      "strengthen your answer",
                         widget=TextArea(**{'class': 'span5'}))

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
        if kwargs.get('location'):
            self.location.data = kwargs['location']

    def validate(self, *args, **kwargs):
        success = super(QuestionForm, self).validate(*args, **kwargs)
        if success:
            # check invariants
            if (self.data['correct'] not
                 in self.data['alternatives'].splitlines()):
                (self._fields['correct']
                  .errors.append("Answer not in alternatives"))
                success = False
            if self.data['picture']:
                ext = self.data['picture']['filename'].split('.')[-1].lower()
                if ext not in ('png', 'jpeg', 'jpg'):
                    (self._fields['picture']
                     .errors.append("Picture not a JPG or PNG"))
                    success = False
                #else:
                #    print repr(self.data['picture']['body'])
                #    print len(self.data['picture']['body'])

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
    available = BooleanField("Available", [],
                             description="Decides if you can fly to it")


class DocumentForm(BaseForm):
    source = TextAreaField("Source", [validators.Required()])
    source_format = SelectField("Source format",
          [validators.Required()],
          choices=[('html', 'HTML'),
                   ('markdown', 'Markdown')])
    type = SelectField("Type",
          [validators.Required()],
          choices=[('intro', 'Intro'),
                   ('ambassadors', 'Ambassadors')])

    notes = TextAreaField("Notes")


class AddDocumentForm(DocumentForm):

    location = TextField("Location")
    user = TextField("User")
    category = TextField("Category")


class UserForm(BaseForm):
    username = TextField("Username",
                         [validators.Required()])
    email = TextField("Email")
    first_name = TextField("First name")
    last_name = TextField("Last name")
    superuser = BooleanField("Superuser")
    ambassador = SelectMultipleField("Ambassador of...")

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        self.ambassador.choices = [(x, x)
                                   for x in kwargs['countries']]


class LocationPictureForm(BaseForm):
    location = SelectField("City",
                      [validators.Required()])

    picture = FileField("Picture (JPG or PNG)")#, [validators.Required()])

    title = TextField("Title",
                     [validators.Required(),
                      validators.Length(min=5, max=100)],
                     description="Single line short description",
                     widget=TextInputWithMaxlength(100, attrs={
                       'size': 100,
                       'class': 'span5',
                     }))

    description = TextAreaField("Description",
                   description="Slightly longer description about the picture",
                   widget=TextArea(**{'class': 'span5'}))


    copyright = TextField("Copyright")
    copyright_url = TextField("Copyright URL")

    index = TextField("Sort index",
             description="The higher the number the latest the picture appears"
             )

    published = BooleanField("Published",
                    description="Whether it should immediately appear")

    notes = TextAreaField("Notes",
                          description="Any other private notes",
                         widget=TextArea(**{'class': 'span5'}))


    def __init__(self, *args, **kwargs):
        super(LocationPictureForm, self).__init__(*args, **kwargs)
        self.location.choices = [
          (str(x['_id']), '%s (%s)' % (x['code'], x['country']))
          for x in kwargs['locations']
        ]
        if kwargs.get('location'):
            self.location.data = kwargs['location']

        if kwargs.get('picture_required'):
            self.picture.validators.append(validators.Required())
