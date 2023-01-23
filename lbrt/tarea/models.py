from django.db import models
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from django_celery_results.models import TaskResult

# Create your models here.


class Order(models.Model):
    inicio = models.DateField(auto_now_add=True)
    order_id = models.TextField()
    status = models.TextField(default='Iniciada')


class Task(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name='tasks')
    inicio = models.DateField(auto_now=True, auto_now_add=False)
    task_name = models.TextField()
    task_id = models.TextField()
    task_object = models.ForeignKey(
        TaskResult, to_field='id', on_delete=models.PROTECT, null=True, related_name='tasks_results')
