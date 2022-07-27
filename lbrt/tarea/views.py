from django.contrib import messages
from django.views.generic import TemplateView

from datetime import datetime, timedelta, date
from dateutil import tz
from django.utils import timezone
import pytz

from . import nicehash
import requests
import json

from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from django_celery_results.models import TaskResult

from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required

from decouple import config

@method_decorator(staff_member_required, name='dispatch')
class TareaView(TemplateView):

    template_name = 'tarea/tarea.html'

    
    #print(pools_on_fist_page)
    #pools=json.loads(pools_on_fist_page)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hora= datetime.now().hour
        context['hora'] = str(hora).zfill(2)
        
        minuto=datetime.now()
        #minuto=minuto+timedelta(minutes=1)
        context['minuto'] = str(minuto.minute).zfill(2)

        context['segundo'] =  datetime.now().second

      
        
        host=config('HOST_NC')
        organization_id=config('ORG_ID_NC')
        key=config('KEY_NC')
        secret=config('SECRET_NC')


        private_api = nicehash.private_api(host, organization_id, key
        , secret, True)

        pools_on_fist_page=''
        try:
            #pass
            pools_on_fist_page = private_api.get_my_pools('', '')
        except Exception as inst:
            print('exception?')
            print(type(inst))    # the exception instance
            print(inst.args)     # arguments stored in .args
            print(inst)      

        #print(pools_on_fist_page)
        context['pools']=pools_on_fist_page['list']
        print(len(pools_on_fist_page['list']))
        total_pages=int(pools_on_fist_page['pagination']['totalPageCount'])
        if ( total_pages > 1):
            for i in range(total_pages-1):
                print(i+1)
                pools_on_page = private_api.get_my_pools(i+1, '')
                #print(pools_on_page)
                print(len(pools_on_page['list']))
                context['pools']+=pools_on_page['list']
        #print(context['pools'])
        #price=0.75
        limit=0.03
        #amount=0.001

        #context['price']=price
        context['limit']=limit
        #context['amount']=amount

        schedules=IntervalSchedule.objects.all()
        periodic_tasks=PeriodicTask.objects.order_by('-id').all()
        periodic_tasks=list(periodic_tasks)
        #print(periodic_tasks)
        #class_date = timezone.localtime(self.class_date)
        timezone = pytz.timezone("America/Mexico_City")
        for task in periodic_tasks:
            #print(task.last_run_at.astimezone(timezone).strftime('%H:%M'))
            if (task.last_run_at is not None):
                task.last_run_at=task.last_run_at.astimezone(timezone).strftime('%H:%M')
        #print(schedules.count())
        #print(PeriodicTask.objects.values())
        #print(TaskResult.objects.values())
        #tasks_results=TaskResult.objects.all().values('task_id').distinct()

        tasks_results=TaskResult.objects.order_by('-id').all()[:5]
        context['schedules']=list(schedules)
        context['periodic_tasks']=periodic_tasks
        context['tasks_results']=list(tasks_results)
        context['wsport']=config('WS_PORT')
        #print(context)
        return context