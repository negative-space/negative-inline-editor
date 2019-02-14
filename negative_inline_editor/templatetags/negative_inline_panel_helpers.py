from django.template import Library

register = Library()


@register.filter
def get_form(obj, request):
    return obj.get_form(request)

default_block_img = '/static/editable-model/block.png'
