from async import tasks


if __name__ == '__main__':
    result = tasks.add_together.delay(23, 42)
    result.wait()
