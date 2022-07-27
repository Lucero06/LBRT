import json
from datetime import datetime, timedelta, date,timezone
from dateutil import tz
import time

from celery.result import AsyncResult

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from lbrt.celery import app
from . import tasks
from django_celery_beat.models import CrontabSchedule, PeriodicTask, IntervalSchedule
from . import models

#from channels.consumer import SyncConsumer
#from channels.exceptions import StopConsumer

class TareaConsumer(WebsocketConsumer):


    def connect(self):
        print('channel name')
        print(self.channel_name)
        async_to_sync(self.channel_layer.group_add)("tarea", self.channel_name)
        self.accept()
        

    def receive(self, text_data):
        print('msj recibido')
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message":  str(datetime.now())+' ======= NUEVA TAREA =======' })
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message":  message})
        #NICEHASH
        if('pool' in message['params']):
            pool_id=message['params']['pool'].split('///')[0]
            pool_algorithm=message['params']['pool'].split('///')[1]
            miner=message['params']['pool'].split('///')[2]

        if('amount' in message['params']):
            amount=message['params']['amount']

        if ('limite' in message['params']):
            limite=message['params']['limite']

        if('limite_2' in message['params']):
            limite_2=message['params']['limite_2']

        #END NH
        print(message)
        tipo=message['tipo']
        periodica=message['params']['periodica']

        #if(periodica=='si'):
        if(tipo=='del_task'):
            print('Borrar tarea... ')
            task_id=message['params']['task_id']
            periodica=message['params']['periodica']
            if(periodica=='periodica_si'):
                task=PeriodicTask.objects.get(pk=task_id)
                task.delete()
                print('Tarea borrada')
        elif (tipo=='add_tarea'):

            tipo_nombre=message['params']['tipo_nombre']

            intervalo=message['params']['intervalo']
            tipo_intervalo=message['params']['tipo_intervalo']
            inicio=message['params']['inicio']

            num_pulses=message['params']['num_pulses']
            
            anio=datetime.now().year
            mes=datetime.now().month
            dia=datetime.now().day
            hora=inicio.split(':')[0]
            minuto=inicio.split(':')[1]
            last_run_at=datetime(anio,mes,dia,int(hora),int(minuto))
            print('Task last tun at: ')
            print(last_run_at)
            if (tipo_intervalo=='dia'):
                tipo_intervalo='days'
                last_run_at=last_run_at-timedelta(days=int(intervalo))

            elif (tipo_intervalo=='hora'):
                tipo_intervalo='hours'
                last_run_at=last_run_at-timedelta(hours=int(intervalo))
            elif (tipo_intervalo=='minuto'):
                tipo_intervalo='minutes'
                last_run_at=last_run_at-timedelta(minutes=int(intervalo))
            #print(tipo_intervalo)
            schedule, _ = IntervalSchedule.objects.get_or_create(
                    
                    every=intervalo,
                    period=tipo_intervalo
                )
            print('Schedule creado:')
            print(schedule)

            if (tipo_nombre=='pulses_cicle'):

                #if(periodica=='si'):
                name_tarea=tipo_nombre
                regex='^'+name_tarea+'(_[0-9]+)*$'
                #print(regex)
                periodic_tasks=PeriodicTask.objects.filter(name__regex=regex).all()
                num_periodic_tasks=len(periodic_tasks)
                #print(num_periodic_tasks)
                if (num_periodic_tasks>0):
                    name_last_task=PeriodicTask.objects.filter(name__regex=regex).last().name
                    number_last_task=name_last_task.split('_')[-1]
                    if not(number_last_task.isnumeric()):
                        number_last_task=1
                    #print(number_last_task)
                    name_tarea=name_tarea+'_'+str(int(number_last_task)+1)
                print(name_tarea)
                if(periodica=='si'):
                    cp=PeriodicTask.objects.create(
                    last_run_at=last_run_at,
                    interval=schedule,                  
                    name=name_tarea,
                    task='tarea.tasks.loop_pulsos', 
                    args=json.dumps(
                        [str(self.channel_name),
                        num_pulses,
                        limite, 
                        limite_2, 
                        pool_id,
                        pool_algorithm,
                        amount
                         ])
                    )
                else:
                    cp=PeriodicTask.objects.create(
                    one_off=True,
                    last_run_at=last_run_at,
                    interval=schedule,                  
                    name=name_tarea,
                    task='tarea.tasks.loop_pulsos', 
                    args=json.dumps(
                        [str(self.channel_name),
                        num_pulses,
                        limite, 
                        limite_2, 
                        pool_id,
                        pool_algorithm,
                        amount
                        ])
                    )

                print('Tarea creada: ')
                print(cp)
                print(cp.id)


    def tarea_message(self, event):
        message = event['message']
        print('mensaje')
        print(message)
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
        

    def disconnect(self, close_code):
        print('close coneection ws')
        print(close_code)
        async_to_sync(self.channel_layer.group_discard)("tarea", self.channel_name)
        self.close()
        #raise StopConsumer()