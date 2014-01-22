from ..settings import MEDIA_TREE_MODEL

app, model = MEDIA_TREE_MODEL.split('.')
if app == 'media_tree':
    module = __import__('filenode', globals(), locals(), [model], -1)
    FileNode = getattr(module, model)
else:
    from django.db.models import get_model
    FileNode = get_model(app, model, only_installed=True)