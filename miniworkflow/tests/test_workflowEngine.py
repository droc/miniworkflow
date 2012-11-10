from unittest import TestCase
from miniworkflow import NodeSpec, Transition, PrintDecomposition, Task, Workflow, TaskResult

__author__ = 'Juan'


class ConditionDouble(object):
    def __init__(self):
        self.canned_response = True

    def eval(self, *args):
        return self.canned_response


class AsyncTask(object):
    def __init__(self):
        self.uuid = None

    def execute(self, node, context):
        self.uuid = node.uuid
        print "Async task starting"
        print "uuid: %s" % self.uuid
        return TaskResult.WAIT


class TestWorkflowEngine(TestCase):
    def test_empty_workflow_completes(self):
        node1 = NodeSpec("first")
        node1.add_task(Task(PrintDecomposition()))
        node2 = NodeSpec("second")
        async_task = AsyncTask()
        node2.add_task(async_task)
        node3 = NodeSpec("end")
        condition = ConditionDouble()
        node2.connect(Transition(condition=condition, target_node=node3))
        node1.connect(Transition(condition=condition, target_node=node2))

        w = Workflow({node1.uuid: node1}, {}, node3)
        w.run()

        w2 = Workflow(w.activated_nodes, w.waiting, node3)
        w2.complete_by_id(async_task.uuid)
