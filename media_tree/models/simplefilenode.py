#encoding=utf-8

from media_tree import settings as app_settings
from .base import BaseNode

__all__ = ['SimpleFileNode']

class SimpleFileNode(FileMixin, BaseNode):
    class Meta:
        app_label = 'media_tree'
SimpleFileNode._default_manager = SimpleFileNode.objects