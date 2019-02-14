from .views import update_model
from django.conf.urls import url
from .views import update_sort, ct_items
from .views import upload_image
from .views import delete_image

urlpatterns = (
    url(r'^api/update-model', update_model, name='update_model'),
    url(r'^api/update-sort', update_sort, name='update_sort'),
    url(r'^api/ct_items', ct_items, name='ct_items'),
    url(r'^api/upload_image', upload_image, name='upload_image'),
    url(r'^api/delete_image', delete_image, name='delete_image'),
)
