from app.quote import blueprint
from flask import render_template, session, jsonify
from flask_login import login_required
from flask_socketio import emit
from app.extensions import socketio
import random
from threading import Lock


class CarPrice:
    def __init__(self, make, model, price=None):
        self.make = make
        self.model = model
        self.id = make + model
        self.price = price

    def __repr__(self):
        return 'make:' + self.make + ' model:' + self.model + ' price:' + self.price

    def serialize(self):
        return self.__dict__


cache = {}

for cp in [
    CarPrice("Toyota", "Celica", 35000),
    CarPrice("Ford", "Mondeo", 32000),
    CarPrice("Porsche", "Boxter", 70000)
]:
    cache[cp.id] = cp

thread = None
thread_lock = Lock()
thread_run = False


def create_or_update_quote(quote):
    make = quote.get('make', '')
    model = quote.get('model', '')
    price = quote.get('price', None)
    result = CarPrice(make, model, price)

    # update price
    if result.price:
        result.price *= (1 + random.uniform(-0.1, 0.1))
    elif result.make:
        if result.make == 'Toyota':
            result.price = 30000
        elif result.make == 'Ford':
            result.price = 40000
        elif result.make == 'Porsche':
            result.price = 70000
        else:
            result.price = 50000
    else:
        result.price = 0

    cache[result.id] = result

    return result


def background_thread():
    '''
    a background thread to mimic the random quote calculation
    '''
    while thread_run:
        socketio.sleep(1)
        # pick a random quote from cache and update its price
        ql = list(cache.values())
        idx = random.randint(0, len(ql) - 1)
        raw = ql[idx].serialize()
        calculated = create_or_update_quote(raw)
        message = {'info': 'calculated', 'data': calculated.serialize()}
        emit('quote_calc_event', message)


@blueprint.route('/')
@login_required
def quote():
    return render_template('quote.html')


@blueprint.route('/init_grid')
@login_required
def init_grid():
    return jsonify([x.serialize() for x in list(cache.values())])


@socketio.on('quote_update_event', namespace='/quote')
def on_update(message):
    session['receive_count'] = session.get('receive_count', 0) + 1
    # calculate quote
    raw = message['data']
    calculated = create_or_update_quote(raw)
    message = {'info': 'calculated', 'count': session['receive_count'], 'data': calculated.serialize()}
    emit('quote_calc_event', message)


@socketio.on('connect', namespace='/quote')
def on_connect():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('quote_calc_event', {'info': 'connected', 'count': session['receive_count']})


@socketio.on('disconnect', namespace='/quote')
def on_disconnect():
    print('Client disconnected')


@socketio.on('start_subscribe', namespace='/quote')
def on_start_subscribe():
    print('start subscribe')
    global thread_run
    global thread
    with thread_lock:
        if thread is None:
            thread_run = True
            thread = socketio.start_background_task(background_thread)


@socketio.on('stop_subscribe', namespace='/quote')
def on_stop_subscribe():
    print('stop subscribe')
    global thread_run
    global thread
    with thread_lock:
        thread_run = False

