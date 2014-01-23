from ..settings import MEDIA_TREE_MODEL

app, model = MEDIA_TREE_MODEL.split('.')
modeladmin = model + 'Admin'
if app == 'media_tree':
    model_module = __import__('media_tree.models', globals(), locals(),
                              [model], 0)
    admin_module = __import__('filenode_admin', globals(), locals(),
                              [modeladmin], -1)

    FileNode = model_module.FileNode
    FileNodeAdmin = getattr(admin_module, modeladmin)

    from django.contrib import admin
    admin.site.register(FileNode, FileNodeAdmin)