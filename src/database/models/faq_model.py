from tortoise.fields import TextField
from tortoise.models import Model


class FaqModel(Model):
    id = TextField(pk=True)
    title = TextField()
    description = TextField()
