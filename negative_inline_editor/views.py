from django.contrib.contenttypes.models import ContentType
from django.http import Http404, HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.conf import settings


def get_model_by_name(model_name):
    from django.apps import apps

    app_name, model_name = model_name.split('.', 1)
    return apps.get_model(app_name, model_name)

@csrf_exempt
def update_model(request):
    if not request.user or not request.user.is_superuser:
        raise Http404

    model_name = request.POST['editableModel']

    if model_name.split('.')[0] not in getattr(settings, 'NEGATIVE_INLINE_MODELS', ['negative_i18n']):
        raise Exception(f"Application is not registered for inline editing: {model_name.split('.')[0]}")

    model = get_model_by_name(model_name)
    pk = request.POST['editablePk']
    field = request.POST['editableField']
    value = request.POST['value']

    obj = model.objects.get(pk=pk)
    setattr(obj, field, value)
    obj.save()

    return HttpResponse('ok')


@csrf_exempt
def ct_items(request):
    if not request.user or not request.user.is_superuser:
        raise Http404

    data = {}
    for oid in request.GET['items'].split(','):
        item = ContentType.objects.get(pk=oid)
        model_cls = item.model_class()
        data[oid] = {
            'type_name': model_cls._meta.verbose_name,
            'preview': model_cls.editable_preview() if hasattr(model_cls, 'editable_preview') else ''
        }

    return JsonResponse(data)


@csrf_exempt
def upload_image(request):
    from filer.models import Folder, Image, File
    from .filer import ThumbnailImageField
    from .filer import Size

    if not request.user or not request.user.is_superuser:
        raise Http404

    folder, created = Folder.objects.get_or_create(name='Content images')
    image = Image.objects.create(original_filename=request.FILES['files[]'].name, folder=folder)
    image.file = request.FILES['files[]']
    image.save()

    return JsonResponse({
      "files": [{
        "url": ThumbnailImageField({'thumb': Size(1024, 1024, crop=True, upscale=False)})
            .to_representation(image)['thumb']['url']
      }]
    })


@csrf_exempt
def delete_image(request):

    from easy_thumbnails.models import Thumbnail
    from filer.models import Folder, Image, File
    # if not request.user or not request.user.is_superuser:
    #     raise Http404
    #
    # folder, created = Folder.objects.get_or_create(name='Content images')
    # image = Image.objects.create(original_filename=request.FILES['files[]'].name, folder=folder)
    # image.file = request.FILES['files[]']
    # image.save()

    host, thumb_path = request.POST.get('file').split('/media/')

    thumbnail = Thumbnail.objects.get(name=thumb_path)
    source = thumbnail.source
    image = Image.objects.get(file=source.name)

    image.delete()
    thumbnail.delete()
    source.delete()

    return JsonResponse({
        "status": "deleted"
      # "files": [{
      #   "url": ThumbnailImageField({'thumb': Size(1024, 1024, crop=True, upscale=False)})
      #       .to_representation(image)['thumb']['url']
      # }]
    })


@csrf_exempt
def update_sort(request):
    if not request.user or not request.user.is_superuser:
        raise Http404

    model_name = request.POST['editableModel']

    if model_name.split('.')[0] not in getattr(settings, 'NEGATIVE_INLINE_MODELS', []):
        raise HttpResponseNotAllowed

    model_cls = get_model_by_name(model_name)
    pk = request.POST['editablePk']

    field = request.POST['editableField']
    related = model_cls._meta.get_field(field)

    try:
        from mptt.managers import TreeManager
    except ImportError:
        TreeManager = None

    if TreeManager and isinstance(related.related_model, TreeManager):
        target = related.related_model.objects.get(pk=pk)

        for order, oid in enumerate(request.POST['order'].split(',')):
            item = related.related_model.objects.get(pk=oid)
            model_cls.objects.move_node(item, target, position='last-child')
    else:
        order_field = related.related_model._meta.ordering[0]

        for order, oid in enumerate(request.POST['order'].split(',')):
            item = related.related_model.objects.get(pk=oid)
            setattr(item, order_field, order)
            item.save()

    return HttpResponse('ok')