import os
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from media_tree import settings as app_settings
from media_tree.models import FileNode
from media_tree.utils import get_module_attr


class ThumbnailError(Exception):
    pass


def get_media_backend(fail_silently=True, handles_media_types=None, 
    handles_file_extensions=None):
        """
        Returns the MediaBackend subclass that is configured for use with 
        media_tree.
        """
        backends = app_settings.MEDIA_TREE_MEDIA_BACKENDS
        if not len(backends):
            if not fail_silently:
                raise ImproperlyConfigured(
                    'There is no media backend configured. Please define '
                    'MEDIA_TREE_MEDIA_BACKENDS in your settings.')
            else:
                return False
        
        # Traverse backends until there is one supporting what's requested:
        for path in backends:    
            backend = get_module_attr(path)
            hmt = (not handles_media_types
                   or backend.handles_media_types(handles_media_types))
            hfe = (not handles_file_extensions
                   or backend.handles_file_extensions(handles_file_extensions))
            if hmt and hfe:
                return backend
    
        if not fail_silently:
            raise ImproperlyConfigured('There is no media backend configured '
                                       'to handle the specified file types.')
        return False
    
    
class MediaBackend(object):
    
    SUPPORTED_MEDIA_TYPES = None
    SUPPORTED_FILE_EXTENSIONS = None
    
    @classmethod
    def handles_media_types(cls, media_types):
        return cls.SUPPORTED_MEDIA_TYPES  \
           and len(set(media_types) - set(cls.SUPPORTED_MEDIA_TYPES)) == 0 

    @classmethod
    def handles_file_extensions(cls, file_extensions):
        unsupported = set(file_extensions) - set(cls.SUPPORTED_FILE_EXTENSIONS)
        return cls.SUPPORTED_FILE_EXTENSIONS and len(unsupported) == 0 
    
    @staticmethod
    def get_thumbnail(source, options):
        raise NotImplementedError('Media backends need to implement the '
                                  '`get_thumbnail()` method.')

    @staticmethod
    def get_valid_thumbnail_options():
        raise NotImplementedError('Media backends need to implement the '
                                  '`get_valid_thumbnail_options()` method.')

    @staticmethod
    def get_cache_paths(subdirs=None):
        if not subdirs:
            raise NotImplementedError('Media backends need to implement the '
                                      '`get_cache_paths()` method.')

        paths = []

        for field in FileNode._meta.fields:
            can_upload = isinstance(field, models.FileField) \
                and hasattr(field, 'upload_to')
            if can_upload:
                for subdir in subdirs:
                    paths.append(os.path.join(field.upload_to, subdir))

        return paths