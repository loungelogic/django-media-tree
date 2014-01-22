#encoding=utf-8

from django.db import models

class FileNodeManager(models.Manager):
    """ A special manager that enables you to pass a ``path`` argument to
        :func:`get`, :func:`filter`, and :func:`exclude`, allowing you to 
        retrieve ``FileNode`` objects by their full node path, 
        which consists of the names of its parents and itself,
        e.g. ``"path/to/folder/readme.txt"``. """

    def __init__(self, filter_args={}):
        super(FileNodeManager, self).__init__()
        self.filter_args = filter_args

    def get_query_set(self):
        return super(FileNodeManager, self).get_query_set() \
                                           .filter(**self.filter_args)

    def get_filter_args_with_path(self, for_self, **kwargs):
        names = kwargs['path'].strip('/').split('/')
        names.reverse()
        parent_arg = '%s'
        new_kwargs = {}
        for index, name in enumerate(names):
            if not for_self or index > 0:
                parent_arg = 'parent__%s' % parent_arg
            new_kwargs[parent_arg % 'name'] = name
        new_kwargs[parent_arg % 'level'] = 0
        new_kwargs.update(kwargs)
        new_kwargs.pop('path')
        return new_kwargs

    def filter(self, *args, **kwargs):
        """ Works just like the default Manager's :func:`filter` method, but
            you can pass an additional keyword argument named ``path``
            specifying the full **path of the folder whose immediate child
            objects** you want to retrieve, e.g. ``"path/to/folder"``. """

        if 'path' in kwargs:
            kwargs = self.get_filter_args_with_path(False, **kwargs)
        return super(FileNodeManager, self).filter(*args, **kwargs)

    def exclude(self, *args, **kwargs):
        """ Works just like the default Manager's :func:`exclude` method, but
            you can pass an additional keyword argument named ``path``
            specifying the full **path of the folder whose immediate child
            objects** you want to exclude, e.g. ``"path/to/folder"``. """

        if 'path' in kwargs:
            kwargs = self.get_filter_args_with_path(False, **kwargs)
        return super(FileNodeManager, self).exclude(*args, **kwargs)

    def get(self, *args, **kwargs):
        """ Works just like the default Manager's :func:`get` method, but
            you can pass an additional keyword argument named ``path``
            specifying the full path of the object you want to retrieve, e.g.
            ``"path/to/folder/readme.txt"``. """

        if 'path' in kwargs:
            kwargs = self.get_filter_args_with_path(True, **kwargs)
        return super(FileNodeManager, self).get(*args, **kwargs)