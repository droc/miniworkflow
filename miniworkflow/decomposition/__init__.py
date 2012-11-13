from miniworkflow import TaskResult

class QueueTaskDecomposition(object):
    """
    This won't probably be of much use outside
    its use in tests
    """
    def __init__(self, task_queue):
        self.task_queue = task_queue

    def get_instance(self):
        return self

    def execute(self, node, _):
        self.task_queue.put(node.uuid())
        return TaskResult.WAIT