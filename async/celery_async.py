import datetime
from celery.result import AsyncResult
from celery import Celery


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


def schedule_task_at(task, args, at_time):
    at_time_dt = datetime.datetime.strptime(at_time, '%Y-%m-%d %H:%M:%S')
    return task.apply_async(args, eta=at_time_dt)


def get_task_async_result(task_id):
    """
    Alias for celery's async result
    :param task_id:
    :return:
    """
    return AsyncResult(task_id)


def get_revoked_tasks():
    """
    Get revoked tasks (utilify method as celery doesn't exclude revoked tasks
    from scheduled methods for optimization purposes)
    :return:
    """
    return celery.control.inspect().revoked().values()[0]


def get_task_status(task_id):
    """
    Get the task status as reported by celery OR revoked if in the revoked list
    :param task_id: The task uuid from celery
    :return: string, one of PENDING | REVOKED | SUCCESSFULL
    """
    revoked_tasks = get_revoked_tasks()
    if task_id in revoked_tasks:
        return 'REVOKED'
    async_result = get_task_async_result(task_id)
    return async_result.status


def get_scheduled_tasks():
    """
    Get scheduled tasks which are not revoked.
    :return: A dict of task_id(string): task_eta(datetime.datetime)
    """
    scheduled = celery.control.inspect().scheduled().values()[0]
    revoked_tasks = get_revoked_tasks()
    scheduled_dict = {}
    for task in scheduled:
        task_id = task.get('request', {}).get('id')
        if task_id not in revoked_tasks:
            task_eta = datetime.datetime.strptime(task.get('eta'), '%Y-%m-%dT%H:%M:%S+00:00')
            scheduled_dict[task_id] = task_eta
    return scheduled_dict


def get_task_eta(task_id):
    """
    Get the estimated time that a task will be executed by task uuid
    :param task_id: The task uuid from celery
    :return: datetime object if in the future or None if
    """
    scheduled = get_scheduled_tasks()
    dt = scheduled.get(task_id)
    if dt:
        return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S+00:00')
    return None


def remove_task(task_id):
    """
    Revokes a task by uuid
    :param task_id: The task uuid from celery
    """
    task_async_result = get_task_async_result(task_id)
    task_async_result.revoke()
