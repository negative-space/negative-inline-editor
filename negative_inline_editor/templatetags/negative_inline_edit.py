import os
import re

from django import template
from django.conf import settings
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import MultipleObjectsReturned
from django.urls import reverse
from django.db.models import Model
from django.template import Library, loader
from django.template.defaulttags import ForNode
from django.utils.module_loading import import_string
from django.utils.safestring import mark_safe
from django.utils.translation import get_language

register = Library()


def get_model_by_name(model_name):
    from django.apps import apps

    app_name, model_name = model_name.split('.', 1)
    return apps.get_model(app_name, model_name)


class EditableNode(template.Node):
    def __init__(self, expr, field, html=False):
        self.expr = expr
        self.field = field
        self.html = html

    def render(self, context):
        expr = self.expr
        model = get_model_by_expr(context, expr)

        if not context['request'].session.get('editable'):
            return getattr(model, self.field, None)

        if not context['request'].session.get('editable_inplace'):
            return getattr(model, self.field, None)

        model_cls = '{}.{}'.format(model._meta.app_label, model.__class__.__name__)

        save_url = reverse('update_model')

        return '<span contenteditable="true" data-html="{}" class="editable-model" data-editable-model="{}" data-editable-pk="{}" ' \
               'data-editable-field="{}" data-save-url="{}">{}</span>'.format(
            'true' if self.html else 'false', model_cls, model.pk, self.field, save_url,
            getattr(model, self.field, None)
        )


def get_model_by_expr(context, expr):
    model = template.Variable(expr).resolve(context)
    if not isinstance(model, Model):
        raise ValueError('Left part of expression "{}" do not evaluate to Django model: {}'.format(
            expr,
            repr(model)
        ))
    if model.pk is None:
        raise ValueError(
            'Left part of expression "{}" evaluated to model that have no primary key. Not saved? {}'.format(
                expr,
                repr(model)
            ))
    return model


@register.tag
def editable(parser, token):
    bits = token.split_contents()

    if len(bits) < 2 or len(bits) > 3:
        raise template.TemplateSyntaxError(
            "%r tag requires at least single argument" % token.contents.split()[0]
        )

    expr = bits[1]

    if len(bits) == 3:
        if bits[2] != '@html':
            raise template.TemplateSyntaxError(
                "%r tag requires at least single argument" % token.contents.split()[0]
            )
        html = True
    else:
        html = False

    if '->' not in expr:
        raise template.TemplateSyntaxError(
            "%r tag's argument should be expression in form: model->field" % tag_name
        )

    expr, field = [x.strip() for x in expr.split('->')]

    return EditableNode(expr, field, html=html)


class EditablePanel(object):
    def __init__(self, name, model, field=None, add_btn=None, form_style=False) -> None:
        super().__init__()

        self.name = name
        self.model = model
        self.field = field
        self.add_btn = add_btn

        self.form_style = form_style

        self.model_cls = type(model)
        try:
            self.admin_cls = admin.site._registry[self.model_cls]

            content_type = ContentType.objects.get_for_model(self.model_cls)  # .__class__
            self.model_admin_url = reverse("admin:%s_%s_changelist" % (content_type.app_label, content_type.model)) \
                                   + str(model.id) + '/change/'

        except IndexError:
            self.admin_cls = None

        if not form_style:
            assert self.field
            assert self.add_btn

    @property
    def items(self):
        return [{'obj': x, 'cls': x._meta.verbose_name} for x in getattr(self.model, self.field).all()]


class ForWrappingNode(template.Node):
    def __init__(self, for_node, expr, field, panel_edit, inline_edit, alias):
        self.for_node = for_node
        self.expr = expr
        self.field = field
        self.panel_edit = panel_edit
        self.inline_edit = inline_edit
        self.alias = alias

    def render(self, context):
        if not context['request'].session.get('editable'):
            return self.for_node.render(context)

        model = get_model_by_expr(context, self.expr)

        model_cls = '{}.{}'.format(model._meta.app_label, model.__class__.__name__)

        related = get_model_by_name(model_cls)._meta.get_field(self.field)

        content_type = ContentType.objects.get_for_model(related.related_model)  # .__class__
        model_admin_url = reverse("admin:%s_%s_changelist" % (content_type.app_label, content_type.model))

        update_sort_url = reverse('update_sort')
        rendered_for = self.for_node.render(context)

        add_btn = f'<a id="editable-{model_cls}-{model.pk}" class="editable-list-btn" data-editable-model="{model_cls}" data-editable-pk="{model.pk}" ' \
            f'data-editable-field="{self.field}" data-editable-related-field="{related.field.name}" data-related-admin-url="{model_admin_url}" data-update-sort-url="{update_sort_url}"></a>'

        if self.panel_edit:
            if not hasattr(context['request'], 'editable_panels'):
                context['request'].editable_panels = {}

            panel_name = self.alias or related.related_name
            context['request'].editable_panels[panel_name] = EditablePanel(
                name=panel_name,
                model=model,
                field=self.field,
                add_btn=add_btn
            )

        if not self.inline_edit or not context['request'].session.get('editable_inplace'):
            return rendered_for

        return add_btn + rendered_for


@register.tag(name='editable-related')
def editable_list(parser, token):
    bits = token.split_contents()

    panel_edit = False
    inline_edit = True
    alias = None

    panel_expr = re.match('^@(panel|panel_only)(\(([^\)]+)\))?$', bits[-1])

    if panel_expr:
        bits = bits[0:-1]

        panel_type = panel_expr.group(1)
        alias = panel_expr.group(3)

        if panel_type == 'panel':
            panel_edit = True

        elif panel_type == 'panel_only':
            inline_edit = False
            panel_edit = True

    if len(bits) < 4:
        raise template.TemplateSyntaxError("'editable-list' statements should have at least four"
                                           " words: %s" % token.contents)

    is_reversed = bits[-1] == 'reversed'
    in_index = -3 if is_reversed else -2
    if bits[in_index] != 'in':
        raise template.TemplateSyntaxError("'for' statements should use the format"
                                           " 'for x in y': %s" % token.contents)

    loopvars = re.split(r' *, *', ' '.join(bits[1:in_index]))
    for var in loopvars:
        if not var or ' ' in var:
            raise template.TemplateSyntaxError("'for' tag received an invalid argument:"
                                               " %s" % token.contents)

    raw_expr = bits[in_index + 1]

    expr, field = [x.strip() for x in raw_expr.split('->')]

    sequence = parser.compile_filter('{}.{}.all'.format(expr, field))

    nodelist_loop = parser.parse(('end-editable-related',))
    token = parser.next_token()

    # if token.contents == 'empty':
    #     nodelist_empty = parser.parse(('endfor',))
    #     parser.delete_first_token()
    # else:
    nodelist_empty = None

    return ForWrappingNode(
        ForNode(loopvars, sequence, is_reversed, nodelist_loop, nodelist_empty),
        expr,
        field,

        panel_edit=panel_edit,
        inline_edit=inline_edit,
        alias=alias
    )


@register.simple_tag(takes_context=True, name='_')
def translate_inline(context, value):
    from negative_i18n.models import StringTranslation
    from negative_i18n.trans_utils import translate_lazy

    if 'request' in context and context['request'].session.get('editable'):
        if 'disable_i18n_collect' not in context:
            if not hasattr(context['request'], 'editable_strings'):
                context['request'].editable_strings = set()

            context['request'].editable_strings.add(value)

    if not 'request' in context or not context['request'].session.get('editable_inplace'):
        return translate_lazy(value)

    try:
        obj, created = StringTranslation.objects.get_or_create(key=value)
    except MultipleObjectsReturned:
        first = StringTranslation.objects.filter(key=value)[0]
        StringTranslation.objects.exclude(id=first.id).filter(key=value).delete()
        obj, created = first, False

    save_url = reverse('update_model')

    return mark_safe(
        '<span contenteditable="true" class="editable-model" data-editable-model="{}" data-editable-pk="{}" ' \
        'data-editable-field="{}" data-save-url="{}">{}</span>'.format(
            'negative_i18n.StringTranslation', obj.pk, 'translation', save_url, obj.translation or value
        ))


class EditModelNode(template.Node):
    def __init__(self, expr, alias):
        self.expr = expr
        self.alias = alias

    def render(self, context):
        if not context['request'].session.get('editable'):
            return ''

        model = get_model_by_expr(context, self.expr)

        if not hasattr(context['request'], 'editable_panels'):
            context['request'].editable_panels = {}

        panel_name = self.alias or model._meta.verbose_name
        context['request'].editable_panels[panel_name] = EditablePanel(
            name=panel_name,
            model=model,
            form_style=True
        )

        return ''


@register.tag(name='editable-model')
def editable_model(parser, token):
    bits = token.split_contents()

    alias = None

    if len(bits) != 2:
        if len(bits) == 4 and bits[2] == 'as':
            alias = bits[3]
        else:
            raise template.TemplateSyntaxError("'editable-model' statements should have at least two"
                                               " words: %s" % token.contents)

    return EditModelNode(bits[1], alias=alias)


class InlineFormNode(template.Node):
    def __init__(self, form_name, var_name):
        self.form_name = form_name
        self.var_name = var_name

    def render(self, context):
        request = context['request']
        form_cls = import_string(self.form_name)

        if request.method == 'POST':
            form = form_cls(request.POST)

            if form.is_valid():
                form.save()
            else:
                pass
        else:
            form = form_cls()

        context[self.var_name] = form

        return ''


@register.tag
def load_form(parser, token):
    try:
        tag_name, form_name, as_expr, variable_name = token.split_contents()

        if as_expr != 'as':
            raise ValueError

    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires arguments in form: load_form form_name as var_name" % token.contents.split()[0]
        )

    return InlineFormNode(form_name, variable_name)


class EditableWrapNode(template.Node):
    def __init__(self, nodelist):
        self.nodelist = nodelist

    def render(self, context):
        html = self.nodelist.render(context)

        if not context['request'].user.is_superuser:
            return html

        if context['request'].session.get('editable'):
            extra_class = ' open' if context['request'].GET.get('editableTab') else ''
            html = '<div class="cratis-editable-wrapper' + extra_class + '">' + self.nodelist.render(
                context) + '</div>'

        t = loader.get_template('editable-model/panel.html')
        context.push({'langs': settings.LANGUAGES, 'lang': get_language()})
        panel_html = t.render(context.flatten())

        css_file = os.path.dirname(os.path.dirname(__file__)) + '/static/editable-model/editable-model.css'
        with open(css_file) as f:
            css_data = '<style>' + re.sub('\s+', ' ', f.read()) + '</style>'

        return css_data + html + panel_html


@register.tag(name='editable-wrap')
def editable_wrap(parser, token):
    bits = token.split_contents()
    if len(bits) > 1:
        raise template.TemplateSyntaxError("'editable-wrap' statement do not accept arguments")

    nodelist_loop = parser.parse(('end-editable-wrap',))
    token = parser.next_token()
    return EditableWrapNode(nodelist=nodelist_loop)


class WithViewContextNode(template.Node):
    def __init__(self, expr):
        self.expr = expr

    def render(self, context):
        cls = import_string(self.expr)

        view = cls(request=context['request'], kwargs={})

        for key, val in view.get_context_data().items():
            if key not in context:
                context[key] = val

        return ''


@register.tag(name='load-view-context')
def load_view_context(parser, token):
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("'load-view-context' requires argument")

    return WithViewContextNode(expr=bits[1])
