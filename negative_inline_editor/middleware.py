
class EditableMiddleware:
    """Middleware that puts the request object in thread local storage."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_superuser and 'editable' in request.GET:
            request.session['editable'] = request.GET.get('editable') == '1'

        if 'editable' in request.session and not request.user.is_superuser:
            del request.session['editable']

        if request.user.is_superuser and 'editable-inplace' in request.GET:
            request.session['editable_inplace'] = request.GET.get('editable-inplace') == '1'

        if 'editable' in request.session and not request.user.is_superuser:
            del request.session['editable_inplace']

        response = self.get_response(request)

        return response
