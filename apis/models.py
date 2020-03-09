from django.db import models

# Create your models here.


class UserInfo(models.Model):
    user_name = models.CharField(max_length=256)
    access_token = models.CharField(max_length=256)
    ccid = models.CharField(max_length=256)
