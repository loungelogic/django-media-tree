import os

from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib.admin import ModelAdmin
from django.contrib.admin.options import csrf_protect_m
from django.contrib.admin.util import unquote
from django.contrib.admin.views.main import IS_POPUP_VAR
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.exceptions import PermissionDenied, ViewDoesNotExist
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext, ugettext_lazy as _

from media_tree import settings as app_settings
from media_tree.admin.actions import core_actions, maintenance_actions
from media_tree.admin.actions.utils import execute_empty_queryset_action
from media_tree.admin.utils import (set_current_request,
                                    get_request_attr, set_request_attr)
from media_tree.admin.views.change_list import SimpleFileNodeChangeList

from ..forms import SimpleFileForm
from ..models import FileNode


def mt_static(url):
    return static(app_settings.MEDIA_TREE_STATIC_SUBDIR + '/' + url)


class BaseFileNodeAdmin(ModelAdmin):
    change_list_template = 'admin/media_tree/filenode/base_change_list.html'

    list_display = app_settings.MEDIA_TREE_LIST_DISPLAY
    list_filter = app_settings.MEDIA_TREE_LIST_FILTER
    #list_display_links = app_settings.MEDIA_TREE_LIST_DISPLAY_LINKS
    search_fields = app_settings.MEDIA_TREE_SEARCH_FIELDS
    ordering = app_settings.MEDIA_TREE_ORDERING_DEFAULT

    _registered_actions = []

    class Media:
        js = [mt_static('lib/jquery/jquery-1.7.1.min.js'),
              mt_static('lib/jquery/jquery.ui.js'),
              mt_static('lib/jquery/jquery.cookie.js'),

              mt_static('lib/fileuploader.js'),
              mt_static('js/admin_enhancements.js'),
              mt_static('js/django_admin_fileuploader.js')]
        css = {'all': (mt_static('css/swfupload.css'),
                       mt_static('css/ui.css'))}

    # URLs

    def get_urls(self):
        urls = super(BaseFileNodeAdmin, self).get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name

        mt_static = os.path.join(settings.STATIC_ROOT,
                                 app_settings.MEDIA_TREE_STATIC_SUBDIR)

        url_patterns = patterns('',

            url(r'^jsi18n/',
                self.admin_site.admin_view(self.i18n_javascript),
                name='media_tree_jsi18n'),

            url(r'^upload/$',
                self.admin_site.admin_view(self.upload_file_view),
                name='%s_%s_upload' % info),

            # Since Flash Player enforces a same-domain policy, the upload
            # will break if static files are served from another domain. So
            # the built-in static file view is used for the uploader SWF:
            url(r'^static/swfupload\.swf$',
                'django.views.static.serve',
                {'document_root': mt_static,
                 'path': 'lib/swfupload/swfupload_fp10/swfupload.swf'},
                name='%s_%s_static_swfupload_swf' % info))
        url_patterns.extend(urls)
        return url_patterns

    # Actions

    @staticmethod
    def register_action(func, required_perms=None):
        BaseFileNodeAdmin._registered_actions.append({
            'action': func,
            'required_perms': required_perms})

    def get_actions(self, request):
        # In ModelAdmin.get_actions(), actions are disabled if the popup var
        # is present. Since BaseFileNodeAdmin always needs a checkbox, this
        # is circumvented here:

        is_popup_var = request.GET.get(IS_POPUP_VAR, None)
        if IS_POPUP_VAR in request.GET:
            request.GET = request.GET.copy()
            del request.GET[IS_POPUP_VAR]

        # get all actions from parent
        actions = super(BaseFileNodeAdmin, self).get_actions(request)

        # and restore popup var
        if is_popup_var:
            request.GET[IS_POPUP_VAR] = is_popup_var

        return actions

    # Misc getters

    def get_changelist(self, request, **kwargs):
        """ Returns the ChangeList class for use on the changelist page. """
        return SimpleFileNodeChangeList

    def get_form(self, request, *args, **kwargs):
        self.form = SimpleFileForm
        self.fields = self.form.Meta.fields

        form = super(BaseFileNodeAdmin, self).get_form(
            request, *args, **kwargs)
        return form

    # Add view

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        if not extra_context:
            extra_context = {}
        extra_context.update({'breadcrumbs_title': _('Add')})

        set_request_attr(request, 'save_node_type', node_type)
        response = super(BaseFileNodeAdmin, self).add_view(
            request, form_url, extra_context)
        return response

    # Change view

    def change_view(self, request, object_id, extra_context=None):
        try:
            object_id = str(object_id)
            node = get_object_or_404(FileNode, pk=unquote(object_id))
        except ValueError:
            raise Http404
        set_request_attr(request, 'save_node', node)
        if not extra_context:
            extra_context = {}
        extra_context.update({'node': node,})
        return super(BaseFileNodeAdmin, self).change_view(\
            request, object_id, extra_context=extra_context)

    # Changelist view

    def get_changelist_view_options(self, request):
        extra_context = {}

        if app_settings.MEDIA_TREE_SWFUPLOAD:
            app, model = \
                self.model._meta.app_label, self.model._meta.model_name

            extra_context.update({
                'file_types': app_settings.MEDIA_TREE_ALLOWED_FILE_TYPES,
                'file_size_limit': app_settings.MEDIA_TREE_FILE_SIZE_LIMIT,
                'swfupload_flash_url': reverse(
                    'admin:%s_%s_upload' % (app, model)),
                'swfupload_upload_url': reverse(
                    'admin:%s_%s_static_swfupload_swf' % (app, model))})

        return extra_context

    def changelist_view(self, request, extra_context=None):
        response = execute_empty_queryset_action(self, request)
        if response:
            return response

        set_current_request(request)

        if not extra_context:
            extra_context = {}
        extra_context.update(self.get_changelist_view_options(request))

        if request.GET.get(IS_POPUP_VAR, None):
            extra_context.update({'select_button': True})

        response = super(BaseFileNodeAdmin, self) \
            .changelist_view(request, extra_context)
        return response


    # Upload view

    @csrf_protect_m
    @transaction.commit_on_success
    def upload_file_view(self, request):
        """ The upload view is exempted from CSRF protection since SWFUpload
            cannot send cookies (i.e. it can only send cookie values as POST
            values, but that would render this check useless anyway). However,
            Flash Player should already be enforcing a same-domain policy. """

        try:
            if not self.has_add_permission(request):
                raise PermissionDenied

            FILE_PARAM_NAME = 'qqfile'
            self.init_parent_folder(request)

            if request.method == 'POST':

                if request.is_ajax() and request.GET.get(FILE_PARAM_NAME, None):
                    content_file = ContentFile(request.body)
                    uploaded_file = UploadedFile(
                        content_file, request.GET.get(FILE_PARAM_NAME), None,
                        content_file.size)
                    form = UploadForm(request.POST, {'file': uploaded_file})
                else:
                    form = UploadForm(request.POST, request.FILES)

                if form.is_valid():
                    node = FileNode(file=form.cleaned_data['file'],
                                    node_type=media_types.FILE)
                    parent_folder = self.get_parent_folder(request)
                    if not parent_folder.is_top_node():
                        node.parent = parent_folder
                    self.save_model(request, node, None, False)
                    # Respond with 'ok' for the client to verify that the
                    # upload was successful, since sometimes a failed request
                    # would not result in a HTTP error and look like a
                    # successful upload. For instance: When requesting the
                    # admin view without authentication, there is a redirect
                    # to the login form, which to SWFUpload looks like a
                    # successful upload request.
                    if request.is_ajax():
                        return HttpResponse(
                            '{"success": true}',
                            content_type="application/json")
                    else:
                        messages.info(
                            request,
                            _('Successfully uploaded file %s.') % node.name)
                        return HttpResponseRedirect(
                            reverse('admin:%s_%s_changelist' % (
                                self.model._meta.app_label,
                                self.model._meta.model_name)))
                else:
                    # invalid form data
                    if request.is_ajax():
                        return HttpResponse('{"error": "%s"}' % ' '.join(
                            [item for sublist in
                             form.errors.values() for item in sublist]), 
                            content_type="application/json")

            # Form is rendered for troubleshooting SWFUpload. If this form
            # works, the problem is not server-side.
            if not settings.DEBUG:
                raise ViewDoesNotExist
            if request.method == 'GET':
                form = UploadForm()
            return render_to_response(
                'admin/media_tree/filenode/upload_form.html', {'form': form})            

        except Exception as e:
            if request.is_ajax():
                return HttpResponse('{"error": "%s"}' % ugettext('Server Error'), 
                    content_type="application/json")
            else:
                raise

    def i18n_javascript(self, request):
        """ Displays the i18n JavaScript that the Django admin requires.

            This takes into account the USE_I18N setting. If it's set to False,
            the generated JavaScript will be leaner and faster. """
        return javascript_catalog(request, packages=['media_tree'])


BaseFileNodeAdmin.register_action(core_actions.copy_selected)
BaseFileNodeAdmin.register_action(maintenance_actions.delete_orphaned_files,
                                  ('media_tree.manage_filenode',))
BaseFileNodeAdmin.register_action(maintenance_actions.clear_cache,
                                  ('media_tree.manage_filenode',))