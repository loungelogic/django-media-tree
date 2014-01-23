from .base import BaseFileNodeAdmin


class SimpleFileNodeAdmin(BaseFileNodeAdmin):
    def get_form(self, *args, **kwargs):
        self.form = SimpleFileForm
        return super(SimpleFileForm, self).get_form(*args, **kwargs)