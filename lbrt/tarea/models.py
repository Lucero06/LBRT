from django.db import models

# Create your models here.


class Tarea(models.Model):
	inicio = models.DateField()
	effort = models.CharField(max_length=50)
	luck = models.CharField(max_length=50)
	sum_luck = models.CharField( max_length=50)
	sum_prom = models.CharField( max_length=50)
	num_blocks = models.CharField( max_length=50)
	orden_id = models.CharField( max_length=50)
	time = models.CharField( max_length=50)
	limit = models.CharField( max_length=50)
	time_on = models.CharField( max_length=50)
	tipo=models.CharField(max_length=50)


# class TareaPeriodica(models.Model):
# 	task_id = models.TextField()
# 	task_schedule_id = models.TextField()
# 	tipo=models.CharField(max_length=100) #schedule, crontab, solar , etc
# 	running = models.BooleanField()
# 	last_run = models.DateTimeField()
# 	error = models.BooleanField()
# 	last_error = models.DateTimeField()
# 	description_error = models.BooleanField()