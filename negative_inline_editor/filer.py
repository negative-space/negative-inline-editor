

from easy_thumbnails.exceptions import InvalidImageFormatError
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.processors import colorspace, scale_and_crop, background
from filer.models import File

from rest_framework import serializers

from easy_thumbnails.files import get_thumbnailer

class Size(object):
    def __init__(self, width, height, crop=True, upscale=True):
        self.width = width
        self.height = height
        self.crop = crop
        self.upscale = upscale

    def as_dict(self):
        return {"size": (self.width, self.height), "width": self.width,
                "height": self.height, "crop": self.crop, "upscale": self.upscale}


def thumb(image, **kwargs):
    size = Size(**kwargs)
    return get_thumbnailer(image).get_thumbnail(size.as_dict()).url

class ThumbnailImageField(serializers.Field):
    def __init__(self, sizes, **kwargs):
        self.sizes = sizes

        super(ThumbnailImageField, self).__init__(**kwargs)


    def to_representation(self, value):
        try:
            data = {
                'type': 'image',
                'id': value.id
            }
        except AttributeError:
            data = {
                'type': 'image'
            }

        if not value:
            return data


        data['name'] = value.name

        try:
            thumbnailer = get_thumbnailer(value)
            thumbnailer.thumbnail_processors = [colorspace, scale_and_crop, background]

            for name, size_def in self.sizes.items():
                size = size_def.as_dict()

                thumb = thumbnailer.get_thumbnail(size)

                url = thumb.url

                data[name] = {
                    'url': url,
                    'width': size['width'],
                    'height': size['height']
                }
            return data

        except (IOError, InvalidImageFormatError) as e:
            print('WARNING! Invalide image format: %s %s' % (e, repr(value)))
            return {
                'type': 'file',
                'url': value.url
            }

