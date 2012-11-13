from miniworkflow import TaskResult

class QueueTaskDecomposition(object):
    def __init__(self, task_queue):
        self.task_queue = task_queue

    def get_instance(self):
        return self

    def execute(self, node, _):
        self.task_queue.put(node.uuid())
        return TaskResult.WAIT