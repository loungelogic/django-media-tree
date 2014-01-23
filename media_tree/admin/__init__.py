from ..settings import MEDIA_TREE_MODEL

app, model = MEDIA_TREE_MODEL.split('.')
modeladmin = model + 'Admin'
if app == 'media_tree':
    model_module = __import__(
        'media_tree.models', globals(), locals(), [model], 0)
    FileNode = model_module.FileNode
    
    admin_module = __import__(
        model.lower(), globals(), locals(), [modeladmin], -1)
    FileNodeAdmin = getattr(admin_module, modeladmin)

    from django.contrib import admin
    admin.site.register(FileNode, FileNodeAdmin)