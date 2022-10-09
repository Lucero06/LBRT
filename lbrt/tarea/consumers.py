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

    def connect(self): #conexión
        print('channel name')
        print(self.channel_name)
        async_to_sync(self.channel_layer.group_add)("tarea", self.channel_name)
        self.accept()
        
    def receive(self, text_data): #recibir datos de vista usuario
        print('msj recibido')

        #datos recibido de interfaz usuario:
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message":  str(datetime.now())+' ======= NUEVA TAREA =======' })
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message":  message})
        print(message)

        #variables orden nice hash
        pool_id=""
        pool_algorithm=""
        stratum_host_name=""
        amount=""
        limite=""
        
        time_up=0
        porcentaje=0
        porcentaje_decimal=0

        # DATOS PARA ORDEN NICEHASH
        if ('time_up' in message['params']):
            time_up=message['params']['time_up']
            print('tiempo recibido:')
            print(time_up)
            time_up=float(time_up)*60
            print('tiempo convertido a segundos:')
            print(time_up)
            
        if('pool' in message['params']):
            pool_id=message['params']['pool'].split('///')[0]
            pool_algorithm=message['params']['pool'].split('///')[1]
            stratum_host_name=message['params']['pool'].split('///')[2]

            if (stratum_host_name=='etc.2miners.com'):
                porcentaje=5
            elif (stratum_host_name=='etc.poolbinance.com'):
                porcentaje=-3
            elif (stratum_host_name=='eu.etc.k1pool.com'):
                porcentaje=0
            print('porcentaje stratum:')
            print(porcentaje)
            porcentaje_decimal=porcentaje/100
            print(porcentaje_decimal)

        if('amount' in message['params']):
            amount=message['params']['amount']
        if ('limite' in message['params']):
            limite=message['params']['limite']

        
        #END NH

        #DATOS TAREA
        #tipo tarea
        tipo=message['tipo']
        #tipo tarea periodica
        periodica=message['params']['periodica']

        if(tipo=='del_task'):
            print('Borrar tarea periodica... ')
            task_id=message['params']['task_id']
            periodica=message['params']['periodica']
            if(periodica=='periodica_si'):
                task=PeriodicTask.objects.get(pk=task_id)
                task.delete()
                print('Tarea borrada')

        elif (tipo=='add_tarea'):
            print('Crear tarea...')
            
            #DATOS TAREA
            tipo_nombre='Order_up'
            intervalo=message['params']['intervalo']
            tipo_intervalo=message['params']['tipo_intervalo']
            inicio=message['params']['inicio']
            #chain_orders_task=getattr(tasks,'chain_order_up')
            #res = chain_task()
            #print(inicio)
            #exit()
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

            #CREAR INTERVALO
            schedule, _ = IntervalSchedule.objects.get_or_create(
                    every=intervalo,
                    period=tipo_intervalo
                )
            print('Schedule creado:')
            print(schedule)

            # CREAR TAREA
            if (tipo_nombre=='Order_up'):

                #DATOS POR STRATUM

                name_tarea='order_up'
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
                    task='tarea.tasks.chain_order_up', 
                    args=json.dumps([str(self.channel_name),pool_id, pool_algorithm,time_up, amount,limite,porcentaje_decimal,name_tarea])
                    )
                else:
                    cp=PeriodicTask.objects.create(
                    one_off=True,
                    last_run_at=last_run_at,
                    interval=schedule,                  
                    name=name_tarea,
                    task='tarea.tasks.chain_order_up', 
                    args=json.dumps([str(self.channel_name),pool_id, pool_algorithm,time_up, amount,limite,porcentaje_decimal,name_tarea])
                    )

                print('Tarea periodica creada: ')
                print(cp)
                print(cp.id)
                #Tarea_Periodica.objects.create()
           

    def tarea_message(self, event): #enviar mensajes a usuario
        message = event['message']
        print('mensaje')
        print(message)
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
        

    def disconnect(self, close_code): #desconectarse
        print('close coneection ws')
        print(close_code)
        async_to_sync(self.channel_layer.group_discard)("tarea", self.channel_name)
        self.close()
        #raise StopConsumer()