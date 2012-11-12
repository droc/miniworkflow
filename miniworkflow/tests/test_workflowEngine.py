import pydot
from unittest import TestCase
from hamcrest import assert_that, has_length, has_item
from miniworkflow import NodeSpec, Transition, PrintDecomposition, Task, Workflow, TaskResult, WorkflowEvent, DotVisitor

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
        # print "%s node %s" % (event, data)
        self.notifications.setdefault(event, []).append(data)

    def get(self, event):
        return self.notifications.get(event, [])


class EmailReceiverDouble(object):
    def inject(self, email):
        pass


class EventProcessor(object):
    def __init__(self, workflow_base, workflow_factory):
        self.workflow_factory = workflow_factory
        self.workflow_base = workflow_base

    def process(self, event):
        pass


class EmailReceivedEvent(object):
    def apply(self, workflow):
        pass


class WorkflowBaseDouble(object):
    pass


class WorkflowFactory(object):
    pass


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

    def test_full_example(self):
        workflow_base = WorkflowBaseDouble()
        workflow_factory = WorkflowFactory()
        event_processor = EventProcessor(workflow_base, workflow_factory)
        event_processor.process(EmailReceivedEvent())

        start = NodeSpec("start")
        wait_for_imp_mail = NodeSpec("wait_for_imp_mail")
        wait_for_target_mail = NodeSpec("wait_for_target_mail")
        get_target_os = NodeSpec("get_target_os")
        reopen_os_ticket = NodeSpec("reopen_os_ticket")
        get_imp = NodeSpec("get_imp")
        gen_test_case = NodeSpec("gen_test_cases")
        end = NodeSpec("end")

        start.connect(Transition(target_node=wait_for_imp_mail))
        start.connect(Transition(target_node=wait_for_target_mail))

        wait_for_imp_mail.connect(Transition(target_node=get_imp))
        wait_for_target_mail.connect(Transition(target_node=get_target_os))

        get_target_os.connect(Transition(target_node=gen_test_case))
        get_target_os.connect(Transition(target_node=reopen_os_ticket))
        reopen_os_ticket.connect(Transition(target_node=wait_for_target_mail))

        get_imp.connect(Transition(target_node=gen_test_case))

        gen_test_case.connect(Transition(end))

        visitor = DotVisitor()
        start.accept(visitor)
        with open("graph.dot", 'w') as f:
            f.write(visitor.print_it())
#        observer = ObserverDouble()
#        w = Workflow({start.uuid: start}, {}, end, observer)
#        w.run()

        #        email_receiver = EmailReceiverDouble()
        #        #app = App(email_receiver)
        #        start = NodeSpec("first")
        #
        #        end = NodeSpec("end")
        #        email_receiver.inject("")
        #        # -> workflow 1235.. started by receiving email #blah
        #        # -> get_workflow_by_update_id

    def test_and_node_and_loop(self):
        start = NodeSpec("start")
        nodeA = NodeSpec("nodeA")
        nodeB = NodeSpec("nodeB")
