import json
from datetime import datetime, timedelta


from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from . import tasks
from django_celery_beat.models import PeriodicTask, IntervalSchedule

# from channels.consumer import SyncConsumer
# from channels.exceptions import StopConsumer


class TareaConsumer(WebsocketConsumer):

    def connect(self):  # conexión
        print('channel name')
        print(self.channel_name)
        async_to_sync(self.channel_layer.group_add)("tarea", self.channel_name)
        self.accept()

    def receive(self, text_data):  # recibir datos de vista usuario
        print('msj recibido')

        # datos recibido de interfaz usuario:
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                               "message":  str(datetime.now())+' ======= NUEVA TAREA ======='})
        async_to_sync(self.channel_layer.group_send)("tarea", {"type": "tarea.message",
                                                               "message":  message})
        print(message)

        # variables orden nice hash
        pool_id = ""
        pool_algorithm = ""
        stratum_host_name = ""
        amount = 0
        limit_up = 0
        limit_down = 0
        limit = 0
        time_up = 0
        time_down = 0
        porcentaje = 0
        porcentaje_decimal = 0

        # DATOS PARA ORDEN NICEHASH
        if ('time_up' in message['params']):
            time_up = message['params']['time_up']
            time_down = message['params']['time_down']
            print('tiempo recibido:')
            print(time_up)
            time_up = float(time_up)*60
            print('tiempo convertido a segundos:')
            print(time_up)
            time_down = float(time_down)*60
            print(time_down)

        if ('pool' in message['params']):
            pool_id = message['params']['pool'].split('///')[0]
            pool_algorithm = message['params']['pool'].split('///')[1]
            stratum_host_name = message['params']['pool'].split('///')[2]
            # if (stratum_host_name == 'etc.2miners.com'):
            #     porcentaje = 5
            # elif (stratum_host_name == 'etc.poolbinance.com'):
            #     porcentaje = -3
            # elif (stratum_host_name == 'eu.etc.k1pool.com'):
            #     porcentaje = 0
        porcentaje = 5
        print('porcentaje stratum: +')
        print(porcentaje)
        porcentaje_decimal = porcentaje/100
        print(porcentaje_decimal)

        if ('amount' in message['params']):
            amount = message['params']['amount']
        if ('limit_up' in message['params']):
            limit_up = message['params']['limit_up']
        if ('limit_down' in message['params']):
            limit_down = message['params']['limit_down']
        if ('limit' in message['params']):
            limit = message['params']['limit']
        # END NH

        # DATOS TAREA
        # tipo tarea
        tipo = message['tipo']
        # tipo tarea periodica
        if ('periodica' in message['params']):
            periodica = message['params']['periodica']

        if (tipo == 'del_task'):
            print('Borrar tarea periodica... ')
            task_id = message['params']['task_id']
            periodica = message['params']['periodica']
            if (periodica == 'periodica_si'):
                task = PeriodicTask.objects.get(pk=task_id)
                task.delete()
                print('Tarea borrada')
        elif (tipo == 'stop_order'):
            order_id = message['params']['order_id']
            task = getattr(tasks, 'stop_order')
            r = task.apply_async(args=[order_id])
            print(r)

        elif (tipo == 'stop_task'):
            task_id = message['params']['task_id']
            task = getattr(tasks, 'stop_task')
            r = task.apply_async(args=[task_id])
            print(r)

        elif (tipo == 'add_tarea'):
            print('Crear tarea...')
            tipo_tarea = message['tipo_tarea']

            # DATOS TAREA
            if (tipo_tarea == 'update_limit'):
                exec_tarea = 'tarea.tasks.iniciar_orden'
                name_tarea = 'order_limit_up_down'
                argumentos = [str(self.channel_name), pool_id, pool_algorithm,
                              time_up, time_down, amount, limit_up, limit_down, porcentaje_decimal]

            elif (tipo_tarea == 'update_price'):
                name_tarea = 'order_update_price'
                exec_tarea = 'tarea.tasks.order_price'
                argumentos = [str(self.channel_name), pool_id, pool_algorithm,
                              amount, limit, porcentaje_decimal]
            print(argumentos)
            intervalo = message['params']['intervalo']
            tipo_intervalo = message['params']['tipo_intervalo']
            inicio = message['params']['inicio']
            # chain_orders_task=getattr(tasks,'iniciar_orden')
            # res = chain_task()
            # print(inicio)
            # exit()
            anio = datetime.now().year
            mes = datetime.now().month
            dia = datetime.now().day
            hora = inicio.split(':')[0]
            minuto = inicio.split(':')[1]
            last_run_at = datetime(anio, mes, dia, int(hora), int(minuto))
            print('Task last tun at: ')
            print(last_run_at)
            if (tipo_intervalo == 'dia'):
                tipo_intervalo = 'days'
                last_run_at = last_run_at-timedelta(days=int(intervalo))

            elif (tipo_intervalo == 'hora'):
                tipo_intervalo = 'hours'
                last_run_at = last_run_at-timedelta(hours=int(intervalo))
            elif (tipo_intervalo == 'minuto'):
                tipo_intervalo = 'minutes'
                last_run_at = last_run_at-timedelta(minutes=int(intervalo))
            # print(tipo_intervalo)

            # CREAR INTERVALO
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=intervalo,
                period=tipo_intervalo
            )
            print('Schedule creado:')
            print(schedule)

            # CREAR TAREA
            # name_tarea = 'order_limit_up_down'
            regex = '^'+name_tarea+'(_[0-9]+)*$'
            # print(regex)
            periodic_tasks = PeriodicTask.objects.filter(
                name__regex=regex).all()
            num_periodic_tasks = len(periodic_tasks)
            # print(num_periodic_tasks)
            if (num_periodic_tasks > 0):
                name_last_task = PeriodicTask.objects.filter(
                    name__regex=regex).last().name
                number_last_task = name_last_task.split('_')[-1]
                if not (number_last_task.isnumeric()):
                    number_last_task = 1
                # print(number_last_task)
                name_tarea = name_tarea+'_'+str(int(number_last_task)+1)

            print(name_tarea)
            argumentos.append(name_tarea)

            if (periodica == 'si'):
                cp = PeriodicTask.objects.create(
                    last_run_at=last_run_at,
                    interval=schedule,
                    name=name_tarea,
                    task=exec_tarea,
                    args=json.dumps(argumentos)
                )
            else:
                cp = PeriodicTask.objects.create(
                    one_off=True,
                    last_run_at=last_run_at,
                    interval=schedule,
                    name=name_tarea,
                    task=exec_tarea,
                    args=json.dumps(argumentos)
                )

            print('Tarea creada: ')
            print(cp)
            print(cp.id)

    def tarea_message(self, event):  # enviar mensajes a usuario
        message = event['message']
        print('mensaje')
        print(message)
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))

    def disconnect(self, close_code):  # desconectarse
        print('close coneection ws')
        print(close_code)
        async_to_sync(self.channel_layer.group_discard)(
            "tarea", self.channel_name)
        self.close()
        # raise StopConsumer()
