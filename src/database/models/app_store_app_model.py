from tortoise.fields import DatetimeField, TextField
from tortoise.models import Model


class AppStoreAppModel(Model):
    version = TextField(pk=True)
    release_notes = TextField()
    release_date = DatetimeField()
