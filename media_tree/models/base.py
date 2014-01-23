#encoding=utf-8

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from media_tree import settings as app_settings
from media_tree.utils import get_media_storage
from mptt.managers import TreeManager
from .managers import FileNodeManager


class BaseFileNode(models.Model):
    """ A stripped-down abstract base class concerning itself with
        file storage. """

    # Meta

    class Meta:
        abstract = True
        permissions = (("manage_filenode", _("Can perform management tasks")),)
        verbose_name = _('file node')
        verbose_name_plural = _('file node')

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
        return super(BaseFileNode, self).save(*args, **kwargs)