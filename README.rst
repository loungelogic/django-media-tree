Django Media Tree
*****************

This is a fork of Django Media Tree intending to improve compatibility with
more recent versions of Django and make the project easier to install and use.
Our changes currently break compatibility with 

Django Media Tree is a Django app for managing your website's media files in a
folder tree, and using them in your own applications. You can browse the full
documentation at http://readthedocs.org/docs/django-media-tree/

What have we changed
====================

* Removed weird dependence on self in ``setup.py``
* Changed old ``{% url admin:... %}`` syntax in the demo project's templates
  to the proper new form ``{% url 'admin:...' %}``
* Changed reference to deprecated argument ``mimetype`` for ``content_type``
* Changed reference to deprecated attribute ``Request.raw_post_data`` in
  ``media_tree/admin/filenode_admin.py`` to ``Request.body``, enabling the
  AJAX uploader to work with Django 1.6+
  
What we're (probably) going to fix next
=======================================

* Improve South compatibility.
* Move most ``FileNode`` metadata to a child class.
* How about a test suite?

Key features
============

* Enables you to organize all of your site media in nested folders.
* Supports various media types (images, audio, video, archives etc).
* Extension system, enabling you to easily add special processing for different
  media types and extend the admin interface.
* Speedy AJAX-enhanced admin interface with drag & drop and dynamic resizing.
* Upload queue with progress indicators (using SWFUpload).
* Add metadata to all media to improve accessibility of your web sites.
* Integration with ``Django CMS <http://www.django-cms.org>``_. Plugins include:
  image, slideshow, gallery, download list -- create your own!
