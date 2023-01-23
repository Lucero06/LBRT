from django.contrib import admin

# Register your models here.
from tarea.models import Order, Task

admin.site.register(Order)
admin.site.register(Task)
