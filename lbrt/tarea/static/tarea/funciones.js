/** @format */

document.querySelector('#btnstart').onclick = function (e) {
	//parametros tarea
	inicio = document.querySelector('#inicio').value;
	tipo_intervalo = document.querySelector('#tipo_intervalo').value;
	intervalo = document.querySelector('#intervalo').value;

	tipo = 'add_tarea';
	tipo_tarea = document.getElementById('task_type').value;

	periodica = 'no';
	if (document.querySelector('#periodica_si').checked == true) {
		periodica = 'si';
	}

	//parametros orden
	if (tipo_tarea == 'update_price') {
		limit = document.querySelector('#id_limit').value;
		amount = document.querySelector('#id_amount').value;
		pool = document.querySelector('#id_pool').value;
		params = {
			inicio: inicio,
			intervalo: intervalo,
			tipo_intervalo: tipo_intervalo,
			periodica: periodica,
			limit: limit,
			amount: amount,
			pool: pool,
		};
	} else {
		limit_up = document.querySelector('#limit_up').value;
		limit_down = document.querySelector('#limit_down').value;
		time_up = document.querySelector('#time_up').value;
		time_down = document.querySelector('#time_down').value;
		pool = document.querySelector('#pools').value;
		amount = document.querySelector('#amount').value;
		params = {
			inicio: inicio,
			amount: amount,
			time_up: time_up,
			time_down: time_down,
			limit_up: limit_up,
			limit_down: limit_down,
			intervalo: intervalo,
			tipo_intervalo: tipo_intervalo,
			periodica: periodica,
			pool: pool,
		};
	}

	console.log(params);
	send_task(params);
	//enviar datos
};

function send_task(params) {
	tareaSocket.send(
		JSON.stringify({
			message: {
				tipo: tipo,
				tipo_tarea: tipo_tarea,
				params: params,
			},
		})
	);
}

function stop_task(task_id) {
	tareaSocket.send(
		JSON.stringify({
			message: {
				tipo: 'stop_task',
				params: {
					task_id: task_id,
				},
			},
		})
	);
}

function stop_order(order_id) {
	tareaSocket.send(
		JSON.stringify({
			message: {
				tipo: 'stop_order',
				params: {
					order_id: order_id,
				},
			},
		})
	);
}

function del_task(id, periodica_yn) {
	tareaSocket.send(
		JSON.stringify({
			message: {
				tipo: 'del_task',
				params: {
					task_id: id,
					periodica: periodica_yn,
				},
			},
		})
	);
}

function hora() {
	const d = new Date();
	let hour = d.getHours();
	let minutes = d.getMinutes();
	minutes = String(minutes).padStart(2, '0');
	hour = String(hour).padStart(2, '0');

	hora_manual = document.querySelector('#inicio').value.split(':');
	tiempo_manual = ''.concat(hora_manual[0], hora_manual[1]);

	tiempo_actual = ''.concat(hour, minutes);

	if (tiempo_manual < tiempo_actual) {
		document.querySelector('#inicio').value = hour + ':' + minutes;
	}

	//console.log(tiempo_manual);
	//console.log(tiempo_actual);
}
