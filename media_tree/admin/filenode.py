# TODO: If in subfolder view, reset_expanded_folders_pk is called and
#       expanded_folders are not stored 
# TODO: Metadata tooltip is too narrow and text gets too wrapped
# TODO: Make renaming of files possible.
# TODO: When files are copied, they lose their human-readable name.
#       Should actually create "File Copy 2.txt".
# TODO: Bug: With child folder changelist view and child of child expanded --
#       after uploading a file, the child of child has the expanded triangle, 
#       but no child child child objects are visible.
#
# Low priority:
#
# TODO: Ordering of tree by column (within parent) should be possible
# TODO: Refactor SWFUpload stuff as extension. This would require signals calls
#       to be called in the SimpleFileNodeAdmin view methods.

import os

import django
from django import forms
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin, messages
from django.contrib.admin import actions, ModelAdmin
from django.contrib.admin.options import csrf_protect_m
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.admin.util import unquote
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import (PermissionDenied, ValidationError,
                                    ViewDoesNotExist)
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.template.defaultfilters import filesizeformat
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode
from django.utils.text import capfirst
from django.utils.translation import ugettext, ugettext_lazy as _

if settings.USE_I18N:
    from django.views.i18n import javascript_catalog
else:
    from django.views.i18n import (
        null_javascript_catalog as javascript_catalog)

from media_tree import media_types, settings as app_settings
from media_tree.admin.actions import core_actions, maintenance_actions
from media_tree.admin.actions.utils import execute_empty_queryset_action
from media_tree.admin.utils import (get_current_request, set_current_request,
                                    get_request_attr, set_request_attr,
                                    is_search_request)
from media_tree.admin.views.change_list import FileNodeChangeList
from media_tree.media_backends import get_media_backend
from media_tree.models import FileNode
from media_tree.widgets import AdminThumbWidget
from media_tree.fields import FileNodeChoiceField
from media_tree.forms import FolderForm, FileForm, SimpleFileForm, UploadForm

try:
    from mptt.admin import MPTTModelAdmin
except ImportError:
    # Legacy mptt support
    from media_tree.contrib.legacy_mptt_support.admin import MPTTModelAdmin

from mptt.forms import TreeNodeChoiceField

from .base import BaseFileNodeAdmin


class FileNodeAdmin(BaseFileNodeAdmin, MPTTModelAdmin):
    """ The FileNodeAdmin aims to let you manage your media files on
        the web like you are used to on your desktop computer.

        Mimicking the file explorer of an operating system, you can browse
        your virtual folder structure, copy and move items, upload more media
        files, and perform many other tasks.

        The SimpleFileNodeAdmin can be used in your own Django projects,
        serving as a file selection dialog when linking ``FileNode`` objects
        to your own models.

        You can also extend the admin interface in many different fashions to
        suit your custom requirements. Please refer to :ref:`extending` for
        more information about extending Media Tree.

        Special features:
        =================

        * The AJAX-enhanced interface allows you to browse your folder tree
          without page reloads.
        * The file listing supports drag & drop. Drag files and folders to
          another folder to move them. Hold the Alt key to copy them.
        * You can set up an upload queue, which enables you to upload large
          files  and monitor the process via the corresponding progress bars. 
        * Drag the slider above the file listing to dynamically
          resize thumbnails.
        * You can select files and execute various special actions on them,
          for instance download the selection as a ZIP archive. """

    change_list_template = 'admin/media_tree/filenode/mptt_change_list.html'
    mptt_indent_field = 'browse_controls'
    mptt_level_indent = app_settings.MEDIA_TREE_MPTT_ADMIN_LEVEL_INDENT

    formfield_overrides = {models.FileField: {'widget': AdminThumbWidget},
                           models.ImageField: {'widget': AdminThumbWidget}}

    # Constructor

    def __init__(self, *args, **kwargs):
        ret = super(BaseFileNodeAdmin, self).__init__(*args, **kwargs)

        # Disable link in first column of changelist
        list_display_links = (None, )

        return ret

    # Actions

    def get_actions(self, request):
        actions = super(FileNodeAdmin, self).get_actions(request)

        # Replace bulk delete method with method that properly updates tree
        # attributes when deleting.
        if 'delete_selected' in actions:
            actions['delete_selected'] = (
                self.delete_selected_tree,
                'delete_selected',
                _("Delete selected %(verbose_name_plural)s"))

        for action_def in BaseFileNodeAdmin._registered_actions:
            perms = not action_def['required_perms'] \
                    or request.user.has_perms(action_def['required_perms'])
            if perms:
                action = self.get_action(action_def['action'])
                actions[action[1]] = action

        return actions

    def delete_selected_tree(self, modeladmin, request, queryset):
        """ Deletes multiple instances and makes sure the MPTT fields get
            recalculated properly. (Because merely doing a bulk delete
            doesn't trigger the post_delete hooks.) """

        # If the user has not yet confirmed the deletion, call the regular
        # delete action that will present a confirmation page
        if not request.POST.get('post'):
            return actions.delete_selected(modeladmin, request, queryset)
        # Otherwise, delete objects one by one
        n = 0
        for obj in queryset:
            obj.delete()
            n += 1
        self.message_user(request, _("Successfully deleted %s items." % n))

    # Misc getters

    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'parent' and issubclass(db_field.rel.to, FileNode):
            # overriding formfield_for_dbfield, thus bypassign both Django's
            # and mptt's formfield_for_foreignkey method, and also preventing
            # Django from wrapping field with RelatedFieldWidgetWrapper ("add"
            # button resulting in a file add form)
            valid_targets = FileNode.tree.filter(
                **db_field.rel.limit_choices_to)
            request = kwargs['request']
            node = get_request_attr(request, 'save_node', None)
            if node:
                # Exclude invalid folders, e.g. node cannot be a child of
                # itself (ripped from mptt.forms.MoveNodeForm)
                opts = node._mptt_meta
                valid_targets = valid_targets.exclude(**{
                    opts.tree_id_attr: getattr(node, opts.tree_id_attr),
                    '%s__gte' % opts.left_attr: getattr(node, opts.left_attr),
                    '%s__lte' % opts.right_attr: getattr(node,
                                                         opts.right_attr)})
            field = FileNodeChoiceField(
                queryset=valid_targets,
                label=capfirst(db_field.verbose_name),
                required=not db_field.blank)
            return field

        return super(BaseFileNodeAdmin, self).formfield_for_dbfield(
            db_field, **kwargs)

    # URLs

    def get_urls(self):
        urls = super(FileNodeAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        url_patterns = patterns('',
            url(r'^add_folder/$',
                self.admin_site.admin_view(self.add_folder_view),
                name='%s_%s_add_folder' % info),
            url(r'^!/(?P<path>.*)/$',
                self.admin_site.admin_view(self.open_path_view),
                name='%s_%s_open_path' % info),
            url(r'^!/$',
                self.admin_site.admin_view(self.open_path_view),
                name='%s_%s_open_root' % info),
            url(r'^(.+)/expand/$',
                self.admin_site.admin_view(self.folder_expand_view),
                name='%s_%s_folder_expand' % info))
        url_patterns.extend(urls)
        return url_patterns

    # Folders

    def init_parent_folder(self, request):
        folder_id = request.GET.get('folder_id', None) \
                    or request.GET.get('parent') \
                    or request.POST.get('parent', None)
        reduce_levels = request.GET.get('reduce_levels', None) \
                        or request.POST.get('reduce_levels', None)

        if folder_id or reduce_levels:
            request.GET = request.GET.copy()
            try:
                del request.GET['folder_id']
            except KeyError:
                pass
            try:
                del request.GET['reduce_levels']
            except KeyError:
                pass

        if folder_id:
            parent_folder = get_object_or_404(
                FileNode, pk=folder_id, node_type=media_types.FOLDER)
        else:
            parent_folder = FileNode.get_top_node()

        if reduce_levels:
            try:
                reduce_levels = int(reduce_levels)
            except ValueError:
                reduce_levels = None

        reset = not reduce_levels \
                and not request.is_ajax() \
                and parent_folder.level >= 0
        if reset:
            self.reset_expanded_folders_pk(request)
            reduce_levels = parent_folder.level + 1

        set_request_attr(request, 'parent_folder', parent_folder)
        set_request_attr(request, 'reduce_levels', reduce_levels)

    def get_parent_folder(self, request):
        return get_request_attr(request, 'parent_folder', None)

    def get_expanded_folders_pk(self, request):
        if not hasattr(request, 'expanded_folders_pk'):
            expanded_folders_pk = []
            cookie = request.COOKIES.get('expanded_folders_pk', None)
            if cookie:
                try:
                    expanded_folders_pk = [int(pk) for pk in cookie.split('|')]
                except ValueError:
                    pass
            # for each folder in the expanded_folders_pk, check if all of its
            # ancestors are also in the list, since a child folder cannot be
            # opened if its parent folders aren't
            for folder in FileNode.objects.filter(pk__in=expanded_folders_pk):
                for ancestor in folder.get_ancestors():
                    expanded = not ancestor.pk in expanded_folders_pk \
                               and folder.pk in expanded_folders_pk
                    if expanded:
                        expanded_folders_pk.remove(folder.pk)
            setattr(request, 'expanded_folders_pk', expanded_folders_pk)

        return getattr(request, 'expanded_folders_pk', None)

    def reset_expanded_folders_pk(self, request):
        setattr(request, 'expanded_folders_pk', [])

    def folder_is_open(self, request, folder):
        return folder.pk in self.get_expanded_folders_pk(request)

    def set_expanded_folders_pk(self, response, expanded_folders_pk):
        response.set_cookie('expanded_folders_pk', '|'.join(
            [str(pk) for pk in expanded_folders_pk]), path='/')

    def get_form(self, request, *args, **kwargs):
        save_node_type = get_request_attr(request, 'save_node_type', None)
        if save_node_type == media_types.FOLDER:
            self.form = FolderForm
        else:
            self.form = FileForm
        self.fieldsets = self.form.Meta.fieldsets

        form = super(SimpleFileNodeAdmin, self).get_form(request, *args, **kwargs)
        form.parent_folder = self.get_parent_folder(request)
        return form

    def save_model(self, request, obj, form, change):
        """ Given a model instance save it to the database. """
        if not change:
            if not obj.node_type:
                obj.node_type = get_request_attr(
                    request, 'save_node_type', None)
        obj.attach_user(request.user, change)
        super(SimpleFileNodeAdmin, self).save_model(request, obj, form, change)

    # List display functions

    def admin_preview(self, node, icons_only=False):
        request = get_current_request()
        template = 'admin/media_tree/filenode/includes/preview.html'
        if not get_media_backend():
            icons_only = True
            template = 'media_tree/filenode/includes/icon.html'
            # TODO SPLIT preview.html in two: one that doesn't need
            # media backend!
        
        thumb_size_key = \
            get_request_attr(request, 'thumbnail_size') or 'default'

        preview = render_to_string(template, {
            'node': node,
            'preview_file': node.get_icon_file() if icons_only \
                else node.get_preview_file(),
            'class': 'collapsed' if node.is_folder() else '',
            'thumbnail_size': \
                app_settings.MEDIA_TREE_ADMIN_THUMBNAIL_SIZES[thumb_size_key]})
        if node.is_folder():
            preview += render_to_string(template, {
                'node': node,
                'preview_file': node.get_preview_file(
                    default_name='_folder_expanded'),
                'class': 'expanded'})
        return preview
    admin_preview.short_description = ''
    admin_preview.allow_tags = True

    def metadata_check(self, node):
        icon = _boolean_icon(node.has_metadata_including_descendants())
        return '<span class="metadata"><span class="metadata-icon">%s</span>' \
               '<span class="displayed-metadata">%s</span></span>' % (
                   icon, node.get_caption_formatted())
    metadata_check.short_description = _('Metadata')
    metadata_check.allow_tags = True

    def expand_collapse(self, node):
        request = get_current_request()
        if not is_search_request(request):
            rel = 'parent:%i' % node.parent_id if node.parent_id else ''
        else:
            rel = ''
        if hasattr(node, 'reduce_levels'):
            qs_params = {'reduce_levels': node.reduce_levels}
        else:
            qs_params = None
        if node.is_folder():
            empty = ' empty' if node.get_children().count() == 0 else ''
            return '<a href="%s" class="folder-toggle%s" rel="%s">' \
                   '<span>%s</span></a>' % (
                       node.get_admin_url(qs_params), empty, rel, '+')
        else:
            return \
                '<a class="folder-toggle dummy" rel="%s">&nbsp;</a>' % (rel,)
    expand_collapse.short_description = ''
    expand_collapse.allow_tags = True

    def admin_link(self, node, include_preview=False):
        return ('<a class="node-link" href="%s">%s<span class="name">' \
                '%s</span></a>') % (
                    node.get_admin_url(),
                    self.admin_preview(node) if include_preview else '',
                    node.name)

    def browse_controls(self, node):
        state = ''
        if node.is_folder():
            request = get_current_request()
            state = 'expanded' if self.folder_is_open(request, node) \
                else 'collapsed'
        return '<span id="%s" class="node browse-controls %s %s">%s%s</span>' % \
            (self.anchor_name(node), 'folder' if node.is_folder() else 'file',
            state, self.expand_collapse(node), self.admin_link(node, True))
    browse_controls.short_description = ''
    browse_controls.allow_tags = True

    def size_formatted(self, node, with_descendants=True):
        if node.node_type == media_types.FOLDER:
            if with_descendants:
                descendants = node.get_descendants()
                if descendants.count() > 0:
                    size = descendants.aggregate(models.Sum('size'))\
                        ['size__sum']
                else:
                    size = None
            else:
                size = None
        else:
            size = node.size
        if not size:
            return ''
        else:
            return '<span class="filesize">%s</span>' % filesizeformat(size)
    size_formatted.short_description = _('size')
    size_formatted.admin_order_field = 'size'
    size_formatted.allow_tags = True

    def node_tools(self, node):
        tools = ''
        tools += '<li><a class="changelink" href="%s">%s</a></li>' % (
            reverse('admin:%s_%s_change' % (
                        self.model._meta.app_label,
                        self.model._meta.model_name),
                    args=(node.pk,)),
            capfirst(ugettext('change')))
        return '<ul class="node-tools">%s</ul>' % tools
    node_tools.short_description = ''
    node_tools.allow_tags = True

    # Add view

    def _add_node_view(self, request, form_url='', extra_context=None,
                       node_type=media_types.FILE):
        self.init_parent_folder(request)
        parent_folder = self.get_parent_folder(request)
        if not extra_context:
            extra_context = {}
        extra_context.update({'node': parent_folder,
                              'breadcrumbs_title': _('Add')})
        set_request_attr(request, 'save_node_type', node_type)
        response = super(SimpleFileNodeAdmin, self).add_view(
            request, form_url, extra_context)
        not_top = isinstance(response, HttpResponseRedirect) \
                  and not parent_folder.is_top_node()
        if not_top:
            return HttpResponseRedirect(
                reverse('admin:media_tree_filenode_folder_expand', 
                        args=(parent_folder.pk,)))
        return response

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        return self._add_node_view(request, form_url, extra_context,
            node_type=media_types.FILE)

    @csrf_protect_m
    @transaction.commit_on_success
    def add_folder_view(self, request, form_url='', extra_context=None):
        return self._add_node_view(request, form_url, extra_context,
            node_type=media_types.FOLDER)

    # Change view

    def change_view(self, request, object_id, extra_context=None):
        try:
            object_id = str(object_id)
            node = get_object_or_404(FileNode, pk=unquote(object_id))
        except ValueError:
            raise Http404
        set_request_attr(request, 'save_node', node)
        set_request_attr(request, 'save_node_type', node.node_type)
        if not extra_context:
            extra_context = {}
        extra_context.update({'node': node,})
        if node.is_folder():
            extra_context.update({'breadcrumbs_title': capfirst(_('change'))})

        return super(SimpleFileNodeAdmin, self).change_view(\
            request, object_id, extra_context=extra_context)

    # Changelist view

    def get_changelist(self, request, **kwargs):
        return FileNodeChangeList

    def get_changelist_view_options(self, request):
        extra_context = super(FileNodeAdmin, self) \
            .get_changelist_view_options(request)

        if 'thumbnail_size' in request.GET:
            request.GET = request.GET.copy()
            thumb_size_key = request.GET.get('thumbnail_size')
            del request.GET['thumbnail_size']

            sizes = app_settings.MEDIA_TREE_ADMIN_THUMBNAIL_SIZES
            if not thumb_size_key in sizes:
                 thumb_size_key = None
            request.session['thumbnail_size'] = thumb_size_key
        thumb_size_key = request.session.get('thumbnail_size', 'default')
        set_request_attr(request, 'thumbnail_size', thumb_size_key)
        
        extra_context.update({
            'thumbnail_sizes': app_settings.MEDIA_TREE_ADMIN_THUMBNAIL_SIZES,
            'thumbnail_size_key': thumb_size_key})

    def changelist_view(self, request, extra_context=None):
        response = execute_empty_queryset_action(self, request)
        if response:
            return response

        if not is_search_request(request):
            self.init_parent_folder(request)
        else:
            self.reset_expanded_folders_pk(request)
        parent_folder = self.get_parent_folder(request)
        set_current_request(request)

        if not extra_context:
            extra_context = {}

        extra_context.update(self.get_changelist_view_options(request))

        if request.GET.get(IS_POPUP_VAR, None):
            extra_context.update({'select_button': True})

        if parent_folder:
            extra_context.update({'node': parent_folder})

        response = super(SimpleFileNodeAdmin, self)\
            .changelist_view(request, extra_context)
        child = isinstance(response, HttpResponse) \
                and parent_folder and not parent_folder.is_top_node()
        if child:
            expanded_folders_pk = self.get_expanded_folders_pk(request)
            if not parent_folder.pk in expanded_folders_pk:
                expanded_folders_pk.append(parent_folder.pk)
                self.set_expanded_folders_pk(response, expanded_folders_pk)
        return response

    # Folder expand view

    def anchor_name(self, node):
        return 'node-%i' % node.pk

    def folder_expand_view(self, request, object_id, extra_context=None):
        node = get_object_or_404(
            FileNode, pk=unquote(object_id), node_type=media_types.FOLDER)
        expand = list(node.get_ancestors())
        expand.append(node)
        response = HttpResponseRedirect('%s#%s' % (
            reverse('admin:media_tree_filenode_changelist' % (
                self.model._meta.app_label, self.model._meta.model_name)),
            self.anchor_name(node)))
        self.set_expanded_folders_pk(
            response, [expanded.pk for expanded in expand])
        return response

    # Open path view

    def open_path_view(self, request, path=''):
        if path is None or path == '':
            return self.changelist_view(request)
        try:
            obj = FileNode.objects.get(path=path)
        except FileNode.DoesNotExist:
            raise Http404
        if obj.is_folder():
            request.GET = request.GET.copy()
            request.GET['folder_id'] = str(obj.pk)
            return self.changelist_view(request)
        else:
            return self.change_view(request, obj.pk)

BaseFileNodeAdmin.register_action(core_actions.move_selected)
BaseFileNodeAdmin.register_action(core_actions.change_metadata_for_selected)
BaseFileNodeAdmin.register_action(core_actions.expand_selected)
BaseFileNodeAdmin.register_action(core_actions.collapse_selected)
if settings.DEBUG:
    BaseFileNodeAdmin.register_action(maintenance_actions.rebuild_tree,
                                      ('media_tree.manage_filenode',))