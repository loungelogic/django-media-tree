#encoding=utf-8

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from media_tree import settings as app_settings
from media_tree.utils import get_media_storage
from mptt.managers import TreeManager
from .managers import FileNodeManager


class BaseNode(models.Model):
    """ A stripped-down abstract base class defining the functionality
        needed to store a file in a tree-like structure. """

    # Meta

    class Meta:
        abstract = True
        ordering = ['tree_id', 'lft']
        permissions = (("manage_filenode", _("Can perform management tasks")),)
        verbose_name = _('file node')
        verbose_name_plural = _('file node')

    # Constants

    STORAGE = get_media_storage()
    """ An instance of the storage class configured in
        ``settings.MEDIA_TREE_STORAGE``. """

    # Managers

    tree = TreeManager()
    """ MPTT tree manager """

    objects = FileNodeManager()
    """ An instance of the :class:`FileNodeManager` class, providing methods
        for retrieving ``FileNode`` objects by their full node path. """

    # Fields

    file = models.FileField(_('file'), null=True, storage=STORAGE,
                            upload_to=app_settings.MEDIA_TREE_UPLOAD_SUBDIR)
    """ The actual media file. """

    parent = models.ForeignKey('self', verbose_name=_('folder'),
                               related_name='children', null=True, blank=True)
    """ The parent (folder) object of the node. """
    
    # Methods

    def file_path(self):
        return self.file.path if self.file else ''

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

    def prevent_save(self):
        self.save_prevented = True

    def check_save_prevented(self):
        if getattr(self, 'save_prevented', False):
            from django.core.exceptions import ValidationError
            raise ValidationError('Saving was prevented for this'
                                  ' FileNode object.')

    def pre_save(self):
        pass

    def save(self, *args, **kwargs):
        self.check_save_prevented()
        self.pre_save()
        return super(BaseNode, self).save(*args, **kwargs)