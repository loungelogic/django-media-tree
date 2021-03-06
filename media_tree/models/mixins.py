#encoding=utf-8

import mimetypes
import mptt
import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.db import models
from django.template.defaultfilters import slugify
from django.utils import dateformat
from django.utils.encoding import force_unicode
from django.utils.formats import get_format
from django.utils.safestring import mark_safe
from django.utils.text import capfirst
from django.utils.translation import ugettext, ugettext_lazy as _

from media_tree import settings as app_settings, media_types
from media_tree.utils import get_media_storage, multi_splitext, join_formatted
from media_tree.utils.filenode import get_file_link
from media_tree.utils.staticfiles import get_icon_finders
from mptt.managers import TreeManager
from mptt.models import MPTTModel, TreeForeignKey

from PIL import Image

from .managers import FileNodeManager

MIMETYPE_CONTENT_TYPE_MAP = app_settings.MEDIA_TREE_MIMETYPE_CONTENT_TYPE_MAP
EXT_MIMETYPE_MAP = app_settings.MEDIA_TREE_EXT_MIMETYPE_MAP
STATIC_SUBDIR = app_settings.MEDIA_TREE_STATIC_SUBDIR

MEDIA_TYPE_NAMES = app_settings.MEDIA_TREE_CONTENT_TYPES
ICON_FINDERS = get_icon_finders(app_settings.MEDIA_TREE_ICON_FINDERS)


class FileMixin(models.Model):
    class Meta:
        abstract = True

    # Constants

    STORAGE = get_media_storage()
    """ An instance of the storage class configured in
        ``settings.MEDIA_TREE_STORAGE``. """

    # Fields

    file = models.FileField(_('file'), null=True, storage=STORAGE,
                            upload_to=app_settings.MEDIA_TREE_UPLOAD_SUBDIR)
    """ The actual media file. """
    
    # Methods

    def file_path(self):
        return self.file.path if self.file else ''

    def get_qualified_file_url(self, field_name='file'):
        """ Returns a fully qualified URL for the :attr:`file` field,
            including protocol, domain and port. In most cases, you can just
            use ``file.url`` instead, which (depending on your ``MEDIA_URL``)
            may or may not contain the domain. In some cases however, you
            always need a fully qualified URL. This includes, for instance,
            embedding a flash video player from a remote domain and passing
            it a video URL. """
        url = getattr(self, field_name).url
        if '://' in url:
            # `MEDIA_URL` already contains domain
            return url
        protocol = getattr(settings, 'PROTOCOL', 'http')
        domain = Site.objects.get_current().domain
        port = getattr(settings, 'PORT', '')
        url_template = '%(protocol)s://%(domain)s%(port)s%(url)s'
        return url_template % {'protocol': 'http',
                               'domain': domain.rstrip('/'),
                               'port': ':'+port if port else '',
                               'url': url}

    def has_changed(self):
        file_changed = True
        if self.pk:
            try:
                saved_instance = self.__class__.objects.get(pk=self.pk)
                if saved_instance.file == self.file:
                    file_changed = False
            except self.__class__.DoesNotExist:
                pass
        return file_changed

  
class FolderMixin(MPTTModel):
    """ A mixin that defines the difference between a file and a folder,
        allowing files to be nested inside folders and not other files.

        Since the pre_save method of this mixin breaks the inheritance chain
        if the node is a folder, as well as due to some particularities of 
        how the underlying ``MPTTModel`` works, FolderMixin will most likely
        need to precede any other mixins that implement this method. """

    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft']

    # Constants

    FOLDER = media_types.FOLDER
    """ The constant denoting a folder node, used for the :attr:`node_type`
        attribute. """

    FILE = media_types.FILE
    """ The constant denoting a file node, used for the :attr:`node_type`
        attribute. """

    # Managers

    objects = FileNodeManager()
    """ An instance of the :class:`FileNodeManager` class, providing methods
        for retrieving ``FileNode`` objects by their full node path. """

    folders = FileNodeManager({'node_type': FOLDER})
    """ A special manager with the same features as :attr:`objects`,
        but only displaying folder nodes. """

    files = FileNodeManager({'node_type': FILE})
    """ A special manager with the same features as :attr:`objects`,
        but only displaying file nodes, no folder nodes. """

    tree = TreeManager()
    """ MPTT tree manager """

    # Fields

    parent = models.ForeignKey('self', verbose_name=_('folder'),
                               related_name='children', null=True, blank=True)
    """ The parent (folder) object of the node. """

    node_type = models.IntegerField(
        _('node type'), choices=((FOLDER, 'Folder'), (FILE, 'File')),
        editable=False, blank=False, null=False)
    """ Type of the node (:attr:`media_types.FILE` or :attr:`media_types.FOLDER`) """

    is_default = models.BooleanField(
        _('use as default object for folder'), blank=True, default=False,
        help_text=_('The default object of a folder, which can be used for'
                    ' folder previews, etc.'))
    """ Flag whether the file is the default file in its parent folder """

    # Methods

    def __init__(self, *args, **kwargs):
        ret = super(FolderMixin, self).__init__(*args, **kwargs)

        # We can't override any model field, abstract or not, so
        # this is where we limit the choices for the parent field
        # to folders only. django-mptt says it's a good idea to
        # avoid calling get_field_by_name in order to prevent
        # any possible circular imports.
        for field, _ in self._meta.get_fields_with_model():
            if field.name == self._mptt_meta.parent_attr:
                field.rel.limit_choices_to = {'node_type': media_types.FOLDER}

        return ret

    def pre_save(self):
        if self.node_type == media_types.FOLDER:
            # Admin asserts that folder name is unique under parent.
            # For other inserts:
            self.make_name_unique_numbered(self.name)

            # Work together with MetadataMixin and FileInfoMixin
            if hasattr(self, 'prepare_metadata'):
                self.prepare_metadata()

            return

        super(FolderMixin, self).pre_save()

    def get_folder_tree(self):
        return self._tree_manager.all().filter(node_type=media_types.FOLDER)

    def get_default_file(self, media_types=None):
        if self.node_type == media_types.FOLDER:
            if not media_types:
                files = self.get_children().filter(node_type=media_types.FILE)
            else:
                files = self.get_children().filter(media_type__in=media_types)
            # TODO the two counts are due to the fact that, at this time,
            # it seems not possible to order the QuerySet returned by
            # get_children() by is_default
            if files.count() > 0:
                default = files.filter(is_default=True)
                if default.count() > 0:
                    return default[0]
                else:
                    return files[0]
            else:
                return None
        else:
            return self

    def get_descendant_count_display(self):
        if self.node_type == media_types.FOLDER:
            return self.get_descendant_count()
        else:
            return ''
    get_descendant_count_display.short_description = _('Items')

    def is_folder(self):
        return self.node_type == media_types.FOLDER

    def is_file(self):
        return self.node_type == media_types.FILE

    @classmethod
    def get_top_node(cls):
        """ Returns a symbolic node representing the root of all nodes.
            This node is not actually stored in the database, but used in the
            admin to link to the change list. """
        return cls(name=('Media objects'), level=-1)

    def is_top_node(self):
        """ Returns True if the model instance is the top node. """
        return self.level == -1

    def get_node_path(self):
        nodes = []
        for node in self.get_ancestors():
            nodes.append(node)
        if (self.level != -1):
            nodes.insert(0, self.get_top_node())
        nodes.append(self)
        return nodes

    def get_path(self):
        path = ''
        for name in [node.name for node in self.get_ancestors()]:
            path = '%s%s/' % (path, name) 
        return '%s%s' % (path, self.name)

    def is_descendant_of(self, ancestor_nodes):
        if issubclass(ancestor_nodes.__class__, self.__class__):
            ancestor_nodes = (ancestor_nodes,)
        # Check whether requested folder is in selected nodes
        is_descendant = self in ancestor_nodes
        if not is_descendant:
            # Check whether requested folder is a subfolder of selected nodes
            ancestors = self.get_ancestors(ascending=True)
            if ancestors:
                self.parent_folder = ancestors[0]
                for ancestor in ancestors:
                    if ancestor in ancestor_nodes:
                        is_descendant = True
                        break
        return is_descendant


class MetadataMixin(models.Model):
    """ A mixin containing a comprehensive set of metadata fields. """

    class Meta:
        abstract = True

    # Managers    

    published_objects = FileNodeManager({'published': True})
    """ A special manager with the same features as :attr:`objects`, but only
        displaying currently published objects. """

    # Fields

    published = models.BooleanField(
        _('is published'), blank=True, default=True)
    """ Is the item published """
    
    title = models.CharField(
        _('title'), max_length=255, default='', null=True, blank=True)
    """ Title for the file """
    
    description = models.TextField(
        _('description'), default='', null=True, blank=True)
    """ Description for the file """

    preview_file = models.ImageField(
        _('preview'), blank=True, null=True,
        upload_to=app_settings.MEDIA_TREE_PREVIEW_SUBDIR,
        help_text=_('Use this field to upload a preview image for video or '
                    'similar media types.'))
    """ An optional image file that will be used for previews. 
        This is useful for video files. """
    
    author = models.CharField(
        _('author'), max_length=255, default='', null=True, blank=True)
    """ Author name of the file """
    
    publish_author = models.BooleanField(_('publish author'), default=False)
    """ Flag to toggle whether the author name should be displayed """
    
    copyright = models.CharField(
        _('copyright'), max_length=255, default='', null=True, blank=True)
    """ Copyright information for the file """
    
    publish_copyright = models.BooleanField(
        _('publish copyright'), default=False)
    """ Flag to toggle whether copyright information should be displayed """
    
    date_time = models.DateTimeField(_('date/time'), null=True, blank=True)
    """ Date and time information for the file (authoring or
        publishing date) """
    
    publish_date_time = models.BooleanField(
        _('publish date/time'), default=False)
    """ Flag to toggle whether date and time information should
        be displayed """
    
    keywords = models.CharField(
        _('keywords'), max_length=255, null=True, blank=True)
    """ Keywords for the file """
    
    override_alt = models.CharField(
        _('alternative text'), max_length=255, default='',
        null=True, blank=True, help_text=_(
            'If you leave this blank, the alternative text will be compiled '
            'automatically from the available metadata.'))
    """ Alt text override. If empty, the alt text will be compiled from
        all metadata that is available and flagged to be displayed. """
    
    override_caption = models.CharField(
        _('caption'), max_length=255, default='', null=True, blank=True,
        help_text=_('If you leave this blank, the caption will be compiled '
                    'automatically from the available metadata.'))
    """ Caption override. If empty, the caption will be compiled from
        all metadata that is available and flagged to be displayed. """

    has_metadata = models.BooleanField(_('metadata entered'), editable=False)
    """ Flag specifying whether the absolute minimal metadata was entered """

    extra_metadata = models.TextField(_('extra metadata'), editable=None)
    """ Extra metadata """

    created = models.DateTimeField(
        _('created'), auto_now_add=True, editable=False)
    """ Date and time when object was created """
    
    modified = models.DateTimeField(
        _('modified'), auto_now=True, editable=False)
    """ Date and time when object was last modified """

    created_by = models.ForeignKey(
        User, verbose_name=_('created by'), related_name='created_by',
        null=True, blank=True, editable=False)
    """ User that created the object """
    
    modified_by = models.ForeignKey(
        User, verbose_name=_('modified by'), related_name='modified_by',
        null=True, blank=True, editable=False)
    """ User that last modified the object """

    slug = models.CharField(
        _('slug'), max_length=255, null=True, editable=False)
    """ Slug for the object """

    # Methods

    def __init__(self, *args, **kwargs):
        ret = super(MetadataMixin, self).__init__(*args, **kwargs)

        for field, _ in self._meta.get_fields_with_model():
            if field.name == 'preview_file':
                field.storage = self.STORAGE

        return ret

    def attach_user(self, user, change):
        if not change:
            self.created_by = user
        self.modified_by = user

    def get_qualified_preview_url(self):
        """ Similar to :func:`get_qualified_file_url`, but returns the URL
            for the :attr:`preview_file` field, which can be used to
            associate image previews with video files. """
        return self.get_qualified_file_url('preview_file')

    def get_icon_file(self, default_name=None):
        if not default_name:
            default_name = '_blank' if not self.is_folder() else '_folder'
        for finder in ICON_FINDERS:
            icon_file = finder.find(self, default_name=default_name)
            if icon_file:
                return icon_file

    def get_preview_file(self, default_name=None):
        """ Returns either :attr:`preview_file` (if set), :attr:`file`
            (if an image), or an icon. """
        if self.preview_file:
            return self.preview_file
        elif self.is_image():
            return self.file
        else:
            return self.get_icon_file(default_name=default_name)

    def prepare_metadata(self):
        needs_folder_info = (hasattr(self, 'node_type')
                             and self.node_type == media_types.FOLDER
                             and hasattr(self, 'media_type'))
        if needs_folder_info:
            self.media_type = media_types.FOLDER
        self.slug = slugify(self.name)
        self.has_metadata = self.check_minimal_metadata()

    def pre_save(self):
        self.prepare_metadata()
        super(MetadataMixin, self).pre_save()

    def check_minimal_metadata(self):
        metadataless = app_settings.MEDIA_TREE_METADATA_LESS_MEDIA_TYPES
        result = (self.media_type in metadataless and self.name != '') \
                  or (self.title != '' or self.description != '' or \
                      self.override_alt != '' or self.override_caption != '')
        if result and self.node_type == media_types.FOLDER and self.pk:
            result = self.has_metadata_including_descendants()
        return result

    def get_metadata_display(self, field_formats = {}, escape=True):
        """ Returns object metadata that has been selected to be displayed to
        users, compiled as a string. """

        def field_format(field):
            if field in field_formats:
                return field_formats[field]
            return u'%s'
        t = join_formatted('', self.title, 
                           format=field_format('title'), escape=escape)
        t = join_formatted(t, self.description, u'%s: %s', escape=escape)
        if self.publish_author:
            t = join_formatted(t, self.author, u'%s' + u' – ' + u'Author: %s',
                               u'%s' + u'Author: %s', escape=escape)
        if self.publish_copyright:
            t = join_formatted(t, self.copyright, u'%s, %s', escape=escape)
        if self.publish_date_time and self.date_time:
            date_time_formatted = dateformat.format(self.date_time,
                                                    get_format('DATE_FORMAT'))
            t = join_formatted(t, date_time_formatted, u'%s (%s)',
                               '%s%s', escape=escape)
        return t
    get_metadata_display.allow_tags = True

    def get_metadata_display_unescaped(self):
        """ Returns object metadata that has been selected to be displayed to
            users, compiled as a string with the original field values left
            unescaped, i.e. the original field values may contain tags. """
        
        return self.get_metadata_display(escape=False)
    get_metadata_display_unescaped.allow_tags = True

    def has_metadata_including_descendants(self):
        if self.node_type == media_types.FOLDER:
            count = self.get_descendants().filter(has_metadata=False).count()
            return count == 0
        else:
            return self.has_metadata
    has_metadata_including_descendants.short_description = _('Metadata')
    has_metadata_including_descendants.boolean = True

    def get_caption_formatted(
        self, field_formats=app_settings.MEDIA_TREE_METADATA_FORMATS,
        escape=True):

        """ Returns object metadata that has been selected to be displayed to
            users, compiled as a string including default formatting, for
            example bold titles.

            You can use this method in templates where you want to output
            image captions. """
        
        if self.override_caption != '':
            return self.override_caption
        else:
            return mark_safe(
                self.get_metadata_display(field_formats, escape=escape))
    get_caption_formatted.allow_tags = True
    get_caption_formatted.short_description = _('displayed metadata')

    def get_caption_formatted_unescaped(self):
        """ Returns object metadata that has been selected to be displayed to
            users, compiled as a string with the original field values left
            unescaped, i.e. the original field values may contain tags. """
        
        return self.get_caption_formatted(escape=False)
    get_caption_formatted_unescaped.allow_tags = True
    get_caption_formatted_unescaped.short_description = _('displayed metadata')

    @property
    def alt(self):
        """ Returns object metadata suitable for use as the HTML ``alt``
            attribute. You can use this method in templates::

            <img src="{{ node.file.url }}" alt="{{ node.alt }}" /> """
        
        if self.override_alt != '' and self.override_alt is not None:
            return self.override_alt
        elif self.override_caption != '' and self.override_caption is not None:
            return self.override_caption
        else:
            return self.get_metadata_display()


class FileInfoMixin(models.Model):

    class Meta:
        abstract = True

    class MPTTMeta:
        order_insertion_by = ['name']

    name = models.CharField(_('name'), max_length=255, null=True)
    """ Name of the file or folder """

    media_type = models.IntegerField(
        _('media type'), choices=app_settings.MEDIA_TREE_CONTENT_TYPE_CHOICES,
        blank=True, null=True, editable=False)
    """ Media type, i.e. broad category of the kind of media """
    
    mimetype = models.CharField(
        _('mimetype'), max_length=64, null=True, editable=False)
    """ The mime type of the media file """

    extension = models.CharField(
        _('type'), default='', max_length=10, null=True, editable=False)
    """ File extension, lowercase """

    size = models.IntegerField(_('size'), null=True, editable=False)
    """ File size in bytes """

    def __unicode__(self):
        return self.name

    def get_media_type_name(self):
        return MEDIA_TYPE_NAMES[self.media_type]

    def make_name_unique_numbered(self, name, ext=''):
        # If file with same name exists in folder:
        qs = self.__class__.objects.filter(parent=self.parent)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        number = 1
        while qs.filter(name__exact=self.name).count() > 0:  # what, really?!
            number += 1
            # rename using a number
            self.name = app_settings.MEDIA_TREE_NAME_UNIQUE_NUMBERED_FORMAT % {
                'name': name, 'number': number, 'ext': ext}

    @staticmethod
    def get_mimetype(filename, fallback_type='application/x-unknown'):
        ext = os.path.splitext(filename)[1].lstrip('.').lower()
        if ext in EXT_MIMETYPE_MAP:
            return EXT_MIMETYPE_MAP[ext]
        else:
            mimetype, encoding = mimetypes.guess_type(filename, strict=False)
            if mimetype:
                return mimetype
            else:
                return fallback_type

    @property
    def mime_supertype(self):
        if self.mimetype:
            return self.mimetype.split('/')[0]

    @property
    def mime_subtype(self):
        if self.mimetype:
            return self.mimetype.split('/')[1]

    @staticmethod
    def mimetype_to_media_type(filename):
        mimetype = self.get_mimetype(filename)
        if mimetype:
            if MIMETYPE_CONTENT_TYPE_MAP.has_key(mimetype):
                return MIMETYPE_CONTENT_TYPE_MAP[mimetype]
            else:
                type, subtype = mimetype.split('/')
                if MIMETYPE_CONTENT_TYPE_MAP.has_key(type):
                    return MIMETYPE_CONTENT_TYPE_MAP[type]
        return media_types.FILE

    def pre_save(self):
        if self.has_changed():
            self.name = os.path.basename(self.file.name)

            # using os.path.splitext(), foo.tar.gz would become
            # foo.tar_2.gz instead of foo_2.tar.gz
            split = multi_splitext(self.name)
            self.make_name_unique_numbered(split[0], split[1])

            # Determine various file parameters
            self.size = self.file.size
            self.extension = split[2].lstrip('.').lower()
            
            self.file.name = self.name
            # TODO: A hash (created by storage class!) would be great
            # because it would obscure file names, but it would be
            # inconvenient for downloadable files
            self.file.name = str(uuid.uuid4()) + '.' + self.extension

        super(FileInfoMixin, self).pre_save()


class ImageMixin(models.Model):

    class Meta:
        abstract = True

    # Fields 

    width = models.IntegerField(
        _('width'), null=True, blank=True,
        help_text=_('Detected automatically for supported images'))
    """ For images: width in pixels """
    
    height = models.IntegerField(
        _('height'), null=True, blank=True,
        help_text=_('Detected automatically for supported images'))
    """ For images: height in pixels """

    # Methods

    def resolution_formatted(self):
        if self.width and self.height:
            return _(u'%(width)i×%(height)i') % {'width': self.width,
                                                 'height': self.height}
        else:
            return ''
    resolution_formatted.short_description = _('Resolution')
    resolution_formatted.admin_order_field = 'width'

    def is_image(self):
        return self.media_type == media_types.SUPPORTED_IMAGE

    def pre_save(self):
        if self.has_changed():
            self.width, self.height = (None, None)  # Store image dimensions

            # Determine whether file is a supported image:
            try:
                self.saved_image = Image.open(self.file)
                self.media_type = media_types.SUPPORTED_IMAGE
                self.width, self.height = self.saved_image.size
            except IOError:
                self.media_type = \
                    self.__class__.mimetype_to_media_type(self.name)

        super(ImageMixin, self).pre_save()


class PositionMixin(models.Model):

    class Meta:
        abstract = True

    position = models.IntegerField(_('position'), default=0)
    """ Position of the file among its siblings, for manual ordering """


class LinkMixin(models.Model):
    class Meta:
        abstract = True

    @property
    def link(self):
        return getattr(self, 'link_obj', None)

    @link.setter
    def link(self, value):
        self.link_obj = link_obj

    @link.deleter
    def link(self):
        del self.link_obj


class AdminMixin(models.Model):
    class Meta:
        abstract = True

    def get_admin_url(self, query_params=None, use_path=False):
        """ Returns the URL for viewing a FileNode in the admin. """

        if not query_params:
            query_params = {}

        url = ''
        if self.is_top_node():
            url = reverse('admin:media_tree_filenode_changelist');
        elif use_path and (self.is_folder() or self.pk):
            url = reverse('admin:media_tree_filenode_open_path',
                          args=(self.get_path(),))
        elif self.is_folder():
            url = reverse('admin:media_tree_filenode_changelist');
            query_params['folder_id'] = self.pk
        elif self.pk:
            return reverse('admin:media_tree_filenode_change',
                           args=(self.pk,))

        if len(query_params):
            params = ['%s=%s' % (key, value)
                      for key, value in query_params.items()]
            url = '%s?%s' % (url, "&".join(params))

        return url

    def get_admin_link(self):
        link = u'%s: <a href="%s">%s</a>' % (capfirst(self._meta.verbose_name),
                                             self.get_admin_url(),
                                             self.__unicode__())
        return force_unicode(mark_safe(link))

    # Workaround for http://code.djangoproject.com/ticket/11058 --
    # which was apparently fixed in Django 1.2
    def admin_preview(self):
        pass


# class SimpleFileNode(FolderMixin, BaseNode):
#     class Meta:
#         managed = app_settings.MEDIA_TREE_MODEL == 'media_tree.SimpleFileNode'
#         verbose_name = _('file node')
#         verbose_name_plural = _('file node')



from media_tree.utils import autodiscover_media_extensions
autodiscover_media_extensions()