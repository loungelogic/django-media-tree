import os
from django.core.urlresolvers import reverse
from django.forms.widgets import Select, HiddenInput
from django.forms.util import flatatt
from django.contrib.admin.widgets import AdminFileWidget, ForeignKeyRawIdWidget
from django.template.loader import render_to_string
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _
from media_tree import settings as app_settings, media_types
from media_tree.models import FileNode
from media_tree.media_backends import get_media_backend, ThumbnailError

THUMBNAIL_EXTENSIONS = app_settings.MEDIA_TREE_THUMBNAIL_EXTENSIONS
THUMBNAIL_SIZE = app_settings.MEDIA_TREE_THUMBNAIL_SIZES['default']


class FileNodeForeignKeyRawIdWidget(ForeignKeyRawIdWidget):

    # TODO: Bug: When popup is dismissed, label for value is currently
    # not replaced with new label (although value is)

    input_type = 'hidden'

    def label_for_value(self, value):
        key = self.rel.get_related_field().name
        try:
            obj = self.rel.to._default_manager \
                      .using(self.db).get(**{key: value})
            preview = render_to_string(
                'media_tree/filenode/includes/preview.html', 
                {'node': obj, 'preview_file': obj.get_preview_file()})
            return '%s %s' % (preview,
                              super(FileNodeForeignKeyRawIdWidget, self) \
                                  .label_for_value(value))
        except (ValueError, self.rel.to.DoesNotExist):
            return ''


class ThumbnailMixin(object):
    def get_thumbnail_source(self, value):
        raise NotImplementedError

    def render(self, name, value, attrs=None):
        output = super(ThumbnailMixin, self).render(name, value, attrs)
        media_backend = get_media_backend(
            fail_silently=True, handles_media_types=(
                media_types.SUPPORTED_IMAGE,))
        value = self.get_thumbnail_source(value)

        if media_backend and value:
            try:
                thumb_extension = \
                    os.path.splitext(value.name)[1].lstrip('.').lower()
                if not thumb_extension in THUMBNAIL_EXTENSIONS:
                    thumb_extension = None

                thumb = media_backend.get_thumbnail(
                    value, {'size': THUMBNAIL_SIZE})

                if thumb:
                    thumb_html = \
                        u'<img src="%s" alt="%s" width="%i" height="%i" />' % (
                            thumb.url, os.path.basename(value.name),
                            thumb.width, thumb.height) 
                    output = u'<div><div class="thumbnail">%s</div>' \
                              '<p>%s</p></div>' % (thumb_html, output)
            
            except ThumbnailError as inst:
                pass

        return mark_safe(output)


class AdminThumbWidget(ThumbnailMixin, AdminFileWidget):
    """ A Image FileField Widget that shows a thumbnail if it has one. """
    
    def get_thumbnail_source(self, value):
        return value

    def __init__(self, attrs={}):
        super(AdminThumbWidget, self).__init__(attrs)
 

class MediaThumbWidget(ThumbnailMixin, Select):
    """ A ForeignKey Select Widget that shows a thumbnail if it has one. """
    
    def get_thumbnail_source(self, value):
        return FileNode.objects.get(pk=value).file


BTN = '<a{0}>{1}</a>'
WIDGET = ('{0}'
          '<div>{1}</div> '
          '<ul class="object-tools"><li>{2}</li><li>{3}</li></ul>')

class MediaPopupWidget(ThumbnailMixin, HiddenInput):
    class Media:
        js = ('media_tree/js/media_popup.js',)

    def get_thumbnail_source(self, value):
        return FileNode.objects.get(pk=value).file

    def render(self, name, value, attrs=None):
        # Render actual input tag - an <input type="hidden">
        # which will be manipulated via JS.
        input_tag = super(MediaPopupWidget, self).render(name, value, attrs)
        print "->", attrs

        value = FileNode.objects.get(pk=value)
        selected_title = value.file.name
        media_title = format_html("<strong>{0}</strong>", selected_title)

        btn_attrs = {'href': reverse('admin:media_tree_filenode_changelist'),
                     'class': 'mediatree-btn-select',
                     'id': attrs['id'] + '-select'}
        button_select = format_html(BTN, flatatt(btn_attrs), _("Select media"))

        btn_attrs = {'href': reverse('admin:media_tree_filenode_add'),
                     'class': 'mediatree-btn-upload',
                     'id': attrs['id'] + '-upload'}
        button_upload = format_html(BTN, flatatt(btn_attrs), _("Upload media"))

        return format_html(
            WIDGET, input_tag, media_title, button_select, button_upload)