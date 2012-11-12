from unittest import TestCase
from hamcrest import assert_that, has_length, has_item
from miniworkflow import NodeSpec, Transition, PrintDecomposition, Task, Workflow, TaskResult, WorkflowEvent

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
        #print "Async task starting"
        #print "uuid: %s" % self.uuid
        return TaskResult.WAIT


class ObserverDouble(object):
    def __init__(self):
        self.notifications = {}

    def notify(self, event, data):
        #print "%s node %s" % (event, data)
        self.notifications.setdefault(event, []).append(data)

    def get(self, event):
        return self.notifications.get(event, [])


class TestWorkflowEngine(TestCase):
    def test_workflow_execution_exits_when_no_ready_tasks(self):
        node1 = NodeSpec("first")
        node1.add_task(Task(PrintDecomposition()))
        node2 = NodeSpec("second")
        async_task = AsyncTask()
        node2.add_task(async_task)
        node3 = NodeSpec("end")
        node3.add_task(Task(PrintDecomposition()))
        condition = ConditionDouble()
        node2.connect(Transition(condition=condition, target_node=node3))
        node1.connect(Transition(condition=condition, target_node=node2))
        observer = ObserverDouble()
        w = Workflow({node1.uuid: node1}, {}, node3, observer)
        w.run()
        assert_that(observer.get(WorkflowEvent.NODE_EXECUTE), has_length(2))
        assert_that(observer.get(WorkflowEvent.NODE_WAIT), has_length(1))
        observer2 = ObserverDouble()
        w2 = Workflow(w.activated_nodes, w.waiting, node3, observer2)
        w2.complete_by_id(async_task.uuid)
        assert_that(observer2.get(WorkflowEvent.NODE_EXECUTE), has_item(node3))
