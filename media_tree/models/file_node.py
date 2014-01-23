#encoding=utf-8

""" Please note that the name of this file should always be kept
    different from 'filenode.py'; otherwise, Python's importer can
    get confused and try to import this file instead of the FileNode
    model as selected in media_tree/models/__init__.py. """

import mptt
from .base import BaseNode
from .mixins import FolderMixin, MetadataMixin, FileInfoMixin, ImageMixin, \
                    PositionMixin, LinkMixin, AdminMixin, FileMixin


__all__ = ['FileNode']


class FileNode(FolderMixin, MetadataMixin, FileInfoMixin, ImageMixin, 
               PositionMixin, LinkMixin, AdminMixin, FileMixin, BaseNode):
    """ Each ``FileNode`` instance represents a node in the media object tree,
        that is to say a "file" or "folder". Accordingly, their ``node_type``
        attribute can either be ``media_types.FOLDER``, meaning that they may
        have child nodes, or ``FileNode.FILE``, meaning that they are
        associated to media files in storage and are storing metadata about
        those files.

        .. Note::
           Since ``FileNode`` is a child class of ``MPTTModel``, it inherits
           many methods that facilitate queries and data manipulation when
           working with trees.

        You can access the actual media associated to a ``FileNode`` model
        instance  using the following fields:

        .. role:: descname(literal)
           :class: descname 

        :descname:`file`
            The actual media file

        :descname:`preview_file`
            An optional image file that will be used for previews. This is
            useful  for visual media that PIL cannot read, such as video files.

        These fields are of the class ``FileField``. Please see
        :ref:`configuration` for information on how to configure storage and
        media backend classes. By default, media files are stored in a
        subfolder ``uploads`` under your media root. """

    class Meta:
        app_label = 'media_tree'

    def __init__(self, *args, **kwargs):
        super(FileNode, self).__init__(*args, **kwargs)

# HACK: Override default manager
FileNode._default_manager = FileNode.objects
        
mptt.register(FileNode)