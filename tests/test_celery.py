from async import tasks, celery_async

if __name__ == '__main__':
    task_async_result = celery_async.schedule_task_at(task=tasks.add_together,
                                                      args=(42, 26),
                                                      at_time='2015-11-02 18:00:00')
    task_id = task_async_result.id

    print celery_async.get_task_status(task_id)
    print celery_async.get_task_eta(task_id)
    print celery_async.get_scheduled_tasks()
    celery_async.remove_task(task_id)
    print celery_async.get_scheduled_tasks()
    print celery_async.get_task_status(task_id)
