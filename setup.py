# encoding=utf8
import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

README = read('README.rst')

setup(
    name = "django-media-tree",
    version = "0.7.2",
    url = 'http://github.com/philomat/django-media-tree',
    license = 'BSD',
    description = "Django Media Tree is a Django app for managing your website's media files in a folder tree, and using them in your own applications.",
    long_description = README,

    author = u'Samuel Luescher',
    author_email = 'sam at luescher dot org',
    
    packages = find_packages(),
    include_package_data=True,
    
    install_requires = ['media_tree==0.7.2']
    dependency_links = ['https://github.com/TAMUArch/django-media-tree.git#egg=media_tree-0.7.2']

    classifiers = [
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
    ]
)

print find_packages()
