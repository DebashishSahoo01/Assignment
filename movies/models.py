from django.db import models
from django.contrib.auth.models import User
import uuid

class Collection(models.Model):
    title=models.CharField(max_length=255)
    description=models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    
    def __str__(self):
        return self.title
    
class Movie(models.Model):
    title=models.CharField(max_length=255)
    description=models.TextField()
    genres=models.CharField(max_length=255,blank=True,null=True)
    uuid=models.UUIDField(unique=True,db_index=True)
    collection=models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='movies')
    
    def __str__(self):
        return self.title
