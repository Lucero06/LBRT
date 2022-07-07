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
                                        "message": '======= NUEVA TAREA =======' })
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
                                        "message": message })
        #NICEHASH
        if('pool' in message['params']):
            pool_id=message['params']['pool'].split('///')[0]
            pool_algorithm=message['params']['pool'].split('///')[1]
            miner=message['params']['pool'].split('///')[2]
        if ('miner_find' in message['params']):
            find_miner=message['params']['miner_find']

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

        if(periodica=='si'):
            intervalo=message['params']['intervalo']
            tipo_intervalo=message['params']['tipo_intervalo']
            inicio=message['params']['inicio']

            chain_task=getattr(tasks,'chain_find_blocks')
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
            #tipo_intervalo='IntervalSchedule.'+tipo_intervalo
            #print(tipo_intervalo)
            schedule, _ = IntervalSchedule.objects.get_or_create(
                    
                    every=intervalo,
                    period=tipo_intervalo
                )
            print('Schedule creado:')
            print(schedule)
            
        if(tipo=='del_task'):
            print('Borrar tarea... ')
            task_id=message['params']['task_id']
            periodica=message['params']['periodica']
            if(periodica=='periodica_si'):
                task=PeriodicTask.objects.get(pk=task_id)
                task.delete()
                print('Tarea borrada')

        elif (tipo=='find_blocks'):

            if(periodica=='si'):
                name_tarea='find_blocks'
                regex='^'+name_tarea+'(_[0-9]+)*$'
                #print(regex)
                periodic_tasks=PeriodicTask.objects.filter(name__regex=regex).all()
                num_periodic_tasks=len(periodic_tasks)
                

                #print(num_periodic_tasks)
                if (num_periodic_tasks>0):
                    #number_last_task=1
                
                    #print(PeriodicTask.objects.filter(name__regex=regex).last().name)
                    name_last_task=PeriodicTask.objects.filter(name__regex=regex).last().name
                    #print(name_last_task.split('_'))
                    #print(name_last_task.split('_'))
                    number_last_task=name_last_task.split('_')[-1]
                    if not(number_last_task.isnumeric()):
                        number_last_task=1
                    #print(number_last_task)
                    name_tarea=name_tarea+'_'+str(int(number_last_task)+1)
                print(name_tarea)
                cp=PeriodicTask.objects.create(
                    last_run_at=last_run_at,
                    interval=schedule,                  # we created this above.
                    name=name_tarea,
                    task='tarea.tasks.chain_find_blocks', 
                    args=json.dumps([str(self.channel_name),pool_id, pool_algorithm,find_miner, amount,limite])
                )
                print('Tarea periodica creada: ')
                print(cp)
                print(cp.id)
                #Tarea_Periodica.objects.create()

            else:
                loop=getattr(tasks,'loop_find_n_blocks')
                detener_orden=getattr(tasks,'detener_orden')
                iniciar_orden=getattr(tasks,'iniciar_orden')
                result = (iniciar_orden.s(str(self.channel_name), limite,pool_id,pool_algorithm, amount) | loop.s(str(self.channel_name),find_miner) | detener_orden.s(str(self.channel_name))  )()
                #print(result.get())
                #print(result.parent.get())
                #print(result.parent.parent.get())

        elif (tipo=='ciclo_limit'):

            limite=message['params']['limite']
            limite_2=message['params']['limite_2']
            time_limit=message['params']['time_limit']

            if (periodica=='si'):
                name_tarea='ciclo_limit'
                regex='^'+name_tarea+'(_[0-9]+)*$'
                
                periodic_tasks=PeriodicTask.objects.filter(name__regex=regex).all()
                 #print(num_periodic_tasks)
                num_periodic_tasks=len(periodic_tasks)
                if (num_periodic_tasks>0):
                    name_last_task=PeriodicTask.objects.filter(name__regex=regex).last().name
                    number_last_task=name_last_task.split('_')[-1]
                    if not(number_last_task.isnumeric()):
                        number_last_task=1
                    #print(number_last_task)
                    name_tarea=name_tarea+'_'+str(int(number_last_task)+1)
                print(name_tarea)

                cp=PeriodicTask.objects.create(
                    last_run_at=last_run_at,
                    interval=schedule,                  
                    name=name_tarea,
                    task='tarea.tasks.loop_update_limit',
                    args=json.dumps([str(self.channel_name),pool_id, pool_algorithm,limite,limite_2, amount, time_limit])
                )
                print('Tarea periodica creada: ')
                print(cp)
                print(cp.id)
            else:

                loop=getattr(tasks,'loop_update_limit')
                result=loop.apply_async(args=[str(self.channel_name),pool_id, pool_algorithm, limite,limite_2, amount,time_limit])
                print('tarea terminada: ')
                print(result)
        
        # elif(tipo=='blocks_miner'):
        #     result=getattr(tasks,'start_find_miner').apply_async(args=[str(self.channel_name),'Flexpool.io', limite,limite_2])
        #     task_id=result.id
        #     pass
       
        # elif(tipo=='detener'):
        #     print('detener...')
        #     #app.control.update_state(task_id=message['task_id'], state=states.SUCCESS)
        #     app.control.revoke(message['task_id'], terminate=True)
        #     #AsyncResult(message['task_id']).abort()
        #     async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message", 
        #                                 "message": {'status':'off'
        #                              } })
        # elif (tipo=='editar'):
        #     pass
        else:

            ## TEST INICIAL
            if (message['inicio']!=''):
                tarea=getattr(tasks,'start_tarea')
                pool_id=message['pool'].split('///')[0]
                pool_algorithm=message['pool'].split('///')[1]

                print(message['inicio'])
                current_year = date.today().year
                current_month = date.today().month
                current_day = date.today().day
                tzinfo = tz.gettz('America/Mexico_City')
                print(tzinfo)
                hour=message['inicio'].split(':')[0]
                minute=message['inicio'].split(':')[1]
                segundo=0
                if(str(datetime.now().hour)==str(hour) and str(datetime.now().minute)==str(minute) ):
                    print('igual')
                    segundo=datetime.now().second
                eta=datetime(current_year,current_month,current_day, hour=int(hour),minute=int(minute),second=segundo, microsecond=0,tzinfo=tzinfo)
                print(eta)
                expires=eta+timedelta(seconds=int(float(message['tiempo'])*60))
                #print('expires')
                #print(expires)
                if(message['tiempo']!=''):
                    segundos=int(float(message['tiempo'])*60)
                    #print(segundos)
                    #print(expires)
                    
                    #result=getattr(tasks,'start_tarea').apply_async(args=[str(self.channel_name)], time_limit=segundos)
                    #getattr(tasks,'start_tarea').signature(args=[str(self.channel_name)],time_limit=segundos, immutable=True)
                    #result=tarea.apply_async(args=[str(self.channel_name)], time_limit=segundos, link=tarea.si(str(self.channel_name)))
                    #print(result)
                    #print(result.id)
                    #task_id=result.id
                    #result.AbortableAsyncResult(task_id).abort()
                    #print(int(float(message['tiempo'])*60))                    
                    #getattr(tasks,'detener_tarea').apply_async(args=[str(self.channel_name), task_id],eta=expires)
                    
                    #result=getattr(tasks,'iniciar_orden').apply_async(args=[str(self.channel_name), 0.01,pool_id,pool_algorithm], link=loop.s(str(self.channel_name), link=detener_orden.s()))
                    
                    #print('result... task id ...')
                    #print(result)
                    #print('order id..')
                    #print(result.get())
                    #task_id=result
                    #order_id=result.get()
                else:
                    result=getattr(tasks,'start_tarea').apply_async(args=[str(self.channel_name)],eta=eta)
                
                task_id=result.id

            else:
                result=getattr(tasks,'start_tarea').delay(self.channel_name)
                #task id
                task_id=result.id
                print(task_id)
                if(message['tiempo']!=''):
                    current_year = date.today().year
                    current_month = date.today().month
                    current_day = date.today().day
                    current_hour=datetime.now().hour
                    current_minute=datetime.now().minute
                    current_seconds=datetime.now().second
                    current_microseconds=datetime.now().microsecond
                    tzinfo = tz.gettz('America/Mexico_City')
                    eta=datetime(current_year,current_month,current_day, hour=int(current_hour),minute=int(current_minute),second=current_seconds, microsecond=current_microseconds,tzinfo=tzinfo)
                    print(int(float(message['tiempo'])*60))
                    expires=eta+timedelta(seconds=int(float(message['tiempo'])*60))
                    print(expires)
                    getattr(tasks,'detener_tarea').apply_async(args=[str(self.channel_name), task_id],eta=expires)


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