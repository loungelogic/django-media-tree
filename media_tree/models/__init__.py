from django.core.exceptions import ImproperlyConfigured
from ..settings import MEDIA_TREE_MODEL

app, model = MEDIA_TREE_MODEL.split('.')
FileNode = None

if app == 'media_tree':
    if model == 'FancyFileNode':
        module_name = 'fancyfilenode'
    elif model == 'SimpleFileNode':
        module_name = 'simplefilenode'
    else:
        raise ImproperlyConfigured(
            "django-media-tree does not define model '%s'. "
            "Valid choices are: FancyFileNode, SimpleFileNode." % model)

    module = __import__(module_name, globals(), locals(), [model], -1)
    FileNode = getattr(module, model)
    
else:
    from django.db.models import get_model
    FileNode = get_model(app, model, only_installed=False)
