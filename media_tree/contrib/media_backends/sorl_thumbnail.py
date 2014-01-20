from django.core.exceptions import ImproperlyConfigured
from media_tree import media_types 
from media_tree.media_backends import MediaBackend, ThumbnailError
from sorl.thumbnail import get_thumbnail


class SorlThumbnailBackend(MediaBackend):
    """ Media backend which generates thumbnails using sorl.thumbnail """
    
    SUPPORTED_MEDIA_TYPES = (media_types.SUPPORTED_IMAGE,)

    @staticmethod
    def check_conf():
        if not 'sorl.thumbnail' in settings.INSTALLED_APPS:
            raise ImproperlyConfigured('`sorl.thumbnail` is not in your '
                                       'INSTALLED_APPS.')
    
    @staticmethod
    def get_thumbnail(source, options):
        size = options.pop('size')
        if not isinstance(size, basestring):
            size = 'x'.join([str(s) for s in size])
        try:
            thumbnail = get_thumbnail(source, size, **options)
        except Exception as inst:
            raise ThumbnailError(inst)
        return thumbnail

    @staticmethod
    def get_valid_thumbnail_options():
        return set(['crop', 'upscale', 'quality', 'progressive', 'orientation',
                    'format', 'colorspace', 'padding', 'padding_color',
                    'options'])