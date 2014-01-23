#encoding=utf-8

from django.db import models
from django.utils.translation import ugettext, ugettext_lazy as _
from media_tree import settings as app_settings
from mptt.managers import TreeManager
from .managers import FileNodeManager


class BaseNode(models.Model):
    """ A stripped-down abstract base class which
        provides hooks for pre-save processing. """

    # Meta

    class Meta:
        abstract = True
        permissions = (("manage_filenode", _("Can perform management tasks")),)
        verbose_name = _('file node')
        verbose_name_plural = _('file node')

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