from django.conf import settings
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from media_tree import media_types


MEDIA_TREE_MODEL = \
    getattr(settings, 'MEDIA_TREE_MODEL', 'media_tree.FancyFileNode')
""" Points to the model to be used by ``media_tree`` to represent uploaded
    files.

    This defaults to ``'media_tree.FancyFileNode'`` -- the original FileNode
    model, which includes a number of convenient fields for storing various
    commonly needed file information and metadata. Alternatively, you could
    set this to ``'media_tree.SimpleFileNode'``, which selects a bare-bones
    model containing no metadata at all.

    However, ``media_tree`` recognizes that your use case is likely to
    require storing a custom set of metadata; the base classes and mixins
    provided in ``models.py`` are intended to be used as a starting point
    for the task of defining your own model. Having defined a model of your
    own, just set `MEDIA_TREE_MODEL` to `'your_app.YourModel'` to let
    `media_tree` pick that up.

    Within the ``media_tree`` code, the currently selected model is
    referred to as ``FileNode``. Importing ``media_tree.models.FileNode``
    from your code will also return the correct model. """


MEDIA_TREE_STORAGE = getattr(settings, 'MEDIA_TREE_STORAGE', None)
""" File storage class to be used for any file-related operations when dealing
    with media files.

    This is not set by default, meaning that Django's ```DEFAULT_FILE_STORAGE``
    <https://docs.djangoproject.com/en/dev/ref/settings/#default-file-storage>`_
    will be used. Please refer to the relevant Django documentation on `file
    storage <https://docs.djangoproject.com/en/dev/ref/files/storage/\
#module-django.core.files.storage>`_. """


MEDIA_TREE_MEDIA_BACKENDS = getattr(settings, 'MEDIA_TREE_MEDIA_BACKENDS', ())
""" A tuple of media backends for thumbnail generation and other media-related
    tasks.

    Currently, the only supported backend is
    ``media_tree.contrib.media_backends.easy_thumbnails.\EasyThumbnailsBackend``,
    which depends on ``easy_thumbnails`` to be installed. Please refer to
    :ref:`media-backends` for more information. """


MEDIA_TREE_MEDIA_BACKEND_DEBUG = getattr(settings,
    'MEDIA_TREE_MEDIA_BACKEND_DEBUG', settings.DEBUG)
""" Specifies whether exceptions caused by media backends, such as
    ``ThumbnailError``, should be raised or silently ignored. """


_DEFAULT_LIST_DISPLAY = {
    'media_tree.FileNode': (
        'browse_controls', 'size_formatted', 'extension',
        'resolution_formatted', 'get_descendant_count_display', 'modified',
        'modified_by', 'metadata_check', 'position', 'node_tools'),
    'media_tree.SimpleFileNode': ('file', )}

MEDIA_TREE_LIST_DISPLAY = getattr(settings, 'MEDIA_TREE_LIST_DISPLAY',
    _DEFAULT_LIST_DISPLAY.get(MEDIA_TREE_MODEL, ()))
""" A tuple containing the columns that should be displayed in the
    ``FileNodeAdmin``. Note that the ``browse_controls`` column is necessary
    for the admin to function properly. """


_DEFAULT_LIST_FILTER = {
    'media_tree.FileNode': ('media_type', 'extension', 'has_metadata'),
    'media_tree.SimpleFileNode': ()}

MEDIA_TREE_LIST_FILTER = getattr(settings, 'MEDIA_TREE_LIST_FILTER',
    _DEFAULT_LIST_FILTER.get(MEDIA_TREE_MODEL, ()))
""" A tuple containing the fields that nodes can be filtered by in the
    ``FileNodeAdmin``. """


_DEFAULT_ORDERING = {'media_tree.FileNode': ['name'],
                     'media_tree.SimpleFileNode': ()}
MEDIA_TREE_ORDERING_DEFAULT = _DEFAULT_ORDERING.get(MEDIA_TREE_MODEL, ())


#MEDIA_TREE_LIST_DISPLAY_LINKS = ('name',)


MEDIA_TREE_SEARCH_FIELDS = getattr(settings, 'MEDIA_TREE_SEARCH_FIELDS',
    ('name', 'title', 'description', 'author', 'copyright', 'override_caption',
    'override_alt'))
""" A tuple containing the fields that nodes can be searched by in
    the ``FileNodeAdmin``. """


MEDIA_TREE_UPLOAD_SUBDIR = getattr(settings, 'MEDIA_TREE_UPLOAD_SUBDIR',
    'upload')
""" The name of the folder under your ``MEDIA_ROOT`` where media files
    are stored. """


MEDIA_TREE_PREVIEW_SUBDIR = getattr(settings, 'MEDIA_TREE_PREVIEW_SUBDIR',
    'upload/_preview')
""" The name of the folder under your ``MEDIA_ROOT`` where cached versions
    of mediafiles, e.g. thumbnails, are stored. """


MEDIA_TREE_STATIC_SUBDIR = 'media_tree'


MEDIA_TREE_ICON_DIRS = getattr(settings, 'MEDIA_TREE_ICON_DIRS', (
    'media_tree/img/icons/mimetypes',
))
""" A tuple containing all icon directories. See :ref:`install-icon-sets`
    for more information. """


MEDIA_TREE_ICON_FINDERS = getattr(settings, 'MEDIA_TREE_ICON_FINDERS', (
    'media_tree.utils.staticfiles.MimetypeStaticIconFileFinder',
))


MEDIA_TREE_ADMIN_THUMBNAIL_SIZES = SortedDict((
    ('tiny', (20, 20)),
    ('small', (70, 70)),
    ('default', (100, 100)),
    ('medium', (250, 250)),
    ('large', (400, 400)),
))


MEDIA_TREE_THUMBNAIL_SIZES = MEDIA_TREE_ADMIN_THUMBNAIL_SIZES.copy()
MEDIA_TREE_THUMBNAIL_SIZES.update({
    'full': None, # None means: use original size
})
MEDIA_TREE_THUMBNAIL_SIZES.update(getattr(settings,
    'MEDIA_TREE_THUMBNAIL_SIZES', {}))
""" A dictionary of default thumbnail sizes. You can pass the dictionary key
    to the ``thumbnail`` templatetag instead of a numeric size.

    Default::

        {
            'small': (80, 80),
            'default': (100, 100),
            'medium': (250, 250),
            'large': (400, 400),
            'full': None, # None means: use original size
        } """


MEDIA_TREE_ALLOWED_FILE_TYPES = getattr(
    settings,
    'MEDIA_TREE_ALLOWED_FILE_TYPES',
    ('aac', 'ace', 'ai', 'aiff', 'avi', 'bmp', 'dir', 'doc', 'docx', 'dmg',
     'eps', 'fla', 'flv', 'gif', 'gz', 'hqx', 'htm', 'html', 'ico', 'indd',
     'inx', 'jpg', 'jar', 'jpeg', 'key', 'md', 'mov', 'mp3', 'mp4', 'mpc',
     'mkv', 'mpg', 'mpeg', 'numbers', 'ogg', 'odg', 'odf', 'odp', 'ods', 'odt',
     'otf', 'pages', 'pdf', 'png', 'pps', 'ppsx', 'ps', 'psd', 'rar', 'rm',
     'rst', 'rtf', 'sit', 'swf', 'tar', 'tga', 'tif', 'tiff', 'ttf', 'txt',
     'wav', 'wma', 'wmv', 'xls', 'xlsx', 'xml', 'zip' ))
""" A whitelist of file extensions that can be uploaded. By default, this is
    a comprehensive list of many common media file extensions that shouldn't
    pose a security risk.

    .. Warning::
       Be careful when adding potentially unsafe file extensions to this
       setting, such as executables or scripts, as this possibly opens a door
       to attackers. """


MEDIA_TREE_THUMBNAIL_EXTENSIONS = getattr(settings,
    'MEDIA_TREE_THUMBNAIL_EXTENSIONS', ('jpg', 'png'))
""" Default: ``('jpg', 'png')``

    A tuple of image extensions used for thumbnail files. Note that ``png``
    is in there since you might typically want to preserve the file type of
    PNG images instead of converting them to JPG. """


MEDIA_TREE_FILE_SIZE_LIMIT = getattr(settings, 'MEDIA_TREE_FILE_SIZE_LIMIT',
    1000000000) # 1 GB
""" Default: 1 GB
    Maximum file size for uploaded files. """


MEDIA_TREE_SWFUPLOAD = getattr(settings, 'MEDIA_TREE_SWFUPLOAD', True)
""" Toggles support for SWFUpload on or off. See :ref:`install-swfupload`
    for more information. """


MEDIA_TREE_GLOBAL_THUMBNAIL_OPTIONS = getattr(settings,
    'MEDIA_TREE_GLOBAL_THUMBNAIL_OPTIONS', {})
""" A dictionary of options that should be applied by default when
    generating thumbnails. You might use this, for instance, to sharpen
    all thumbnails. """


MEDIA_TREE_METADATA_FORMATS = getattr(
    settings, 'MEDIA_TREE_METADATA_FORMATS', {'title': '<strong>%s</strong>'})


MEDIA_TREE_EXT_MIMETYPE_MAP = {'flv': 'video/x-flv',}
""" List of mimetypes not convered by the `mimetypes` Python module
    (for instance, .flv is not guessed by `guess_mimetype`.) """


MEDIA_TREE_MPTT_ADMIN_LEVEL_INDENT = getattr(settings,
    'MEDIA_TREE_MPTT_ADMIN_LEVEL_INDENT', 25)


MEDIA_TREE_MIMETYPE_CONTENT_TYPE_MAP = {
    'application/octet-stream': media_types.FILE,
    'application/zip': media_types.ARCHIVE,
    'application/x-rar-compressed': media_types.ARCHIVE,
    'application/x-tar': media_types.ARCHIVE,
    'application/x-ace-compressed': media_types.ARCHIVE,
    'application': media_types.DOCUMENT,
    'audio': media_types.AUDIO,
    'image': media_types.IMAGE,
    'text': media_types.TEXT,
    'video': media_types.VIDEO}


MEDIA_TREE_CONTENT_TYPE_CHOICES = (
    (media_types.FOLDER, _('folder')),
    (media_types.ARCHIVE, _('archive')),
    (media_types.AUDIO, _('audio')),
    (media_types.DOCUMENT, _('document')),
    (media_types.IMAGE, _('image')),
    (media_types.SUPPORTED_IMAGE, _('web image')),
    (media_types.TEXT, _('text')),
    (media_types.VIDEO, _('video')),
    (media_types.FILE, _('other')))


MEDIA_TREE_CONTENT_TYPES = dict(MEDIA_TREE_CONTENT_TYPE_CHOICES)


MEDIA_TREE_LEVEL_INDICATOR = unichr(0x00A0) * 3;


MEDIA_TREE_NAME_UNIQUE_NUMBERED_FORMAT = '%(name)s_%(number)i%(ext)s'


MEDIA_TREE_METADATA_LESS_MEDIA_TYPES = (
    media_types.FOLDER, media_types.DOCUMENT, media_types.ARCHIVE,
    media_types.TEXT)
""" For these media types, no metadata is critically required apart from a
    name, since the files itself contain text and the filename should be
    descriptive already. """
