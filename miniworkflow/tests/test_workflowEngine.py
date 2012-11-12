from Queue import Queue
from unittest import TestCase
from hamcrest import assert_that, equal_to, has_length, has_item
from miniworkflow import Transition, TaskResult, MiniWorkflow, Node, AndActivationPolicy, AlwaysActivatePolicy


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


class QueueTaskDecomposition(object):
    def __init__(self, task_queue):
        self.task_queue = task_queue

    def get_instance(self):
        return self

    def execute(self, node, workflow):
        self.task_queue.put(node.uuid())
        return TaskResult.WAIT


class ExternalProcessDouble(object):
    def __init__(self):
        self.response = {}

    def get_instance(self):
        return self

    def execute(self, node, workflow):
        workflow.update_state(self.response)
        return TaskResult.COMPLETED


class TestWorkflowEngine(TestCase):
    def test_workflow_execution_exits_when_no_ready_tasks(self):
        node1 = Node("first")
        node1.set_decomposition_factory(ExternalProcessDouble())
        node2 = Node("second")
        q = Queue()
        async_task = QueueTaskDecomposition(q)
        node2.set_decomposition_factory(async_task)
        node3 = Node("end")
        node3.set_decomposition_factory(ExternalProcessDouble())
        node2.connect(Transition(condition=lambda *_: True, target_node=node3))
        node1.connect(Transition(condition=lambda *_: True, target_node=node2))
        w = MiniWorkflow(start_node=node1)
        w.run()
        assert_that(w.executed_trace, has_length(1))
        assert_that(w.waiting_list, has_length(1))
        w2 = MiniWorkflow(start_node=node1)
        w2.set_state(w.get_state())
        w2.complete_by_uuid(q.get(), "")
        w2.run(5)
        assert_that(w2.executed_trace, has_item(node3.uuid()))

    def test_and_node_and_loop(self):
        workflow_base = WorkflowBaseDouble()
        workflow_factory = WorkflowFactory()
        event_processor = EventProcessor(workflow_base, workflow_factory)
        event_processor.process(EmailReceivedEvent())

        start = Node("start")
        wait_for_imp_mail = Node("wait_for_imp_mail")
        wait_for_target_mail = Node("wait_for_target_mail")
        get_target_os = Node("get_target_os")
        reopen_os_ticket = Node("reopen_os_ticket")
        get_imp = Node("get_imp")
        gen_test_case = Node("gen_test_cases", activation_policy=AndActivationPolicy())
        end = Node("end")

        start.connect(Transition(target_node=wait_for_imp_mail))
        start.connect(Transition(target_node=wait_for_target_mail))

        wait_for_imp_mail.connect(Transition(target_node=get_imp))
        wait_for_target_mail.connect(Transition(target_node=get_target_os))

        get_target_os.connect(Transition(target_node=gen_test_case))
        get_target_os.connect(Transition(target_node=reopen_os_ticket, condition=lambda *_:False))
        reopen_os_ticket.connect(Transition(target_node=wait_for_target_mail))

        get_imp.connect(Transition(target_node=gen_test_case))

        gen_test_case.connect(Transition(end))

#        visitor = DotVisitor()
#        start.accept(visitor)
#        with open("graph.dot", 'w') as f:
#            f.write(visitor.print_it())
        w = MiniWorkflow(start)
        w.run(50)
        assert_that(w.executed_trace, equal_to(['start', 'wait_for_imp_mail', 'wait_for_target_mail', 'get_imp', 'get_target_os', 'gen_test_cases', 'end']))

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

    def test_conditional_loop(self):
        external_process = ExternalProcessDouble()
        external_process.response = {'foo': {'bar': True}}
        START = Node(description="START", activation_policy=AlwaysActivatePolicy())
        N1 = Node(description="N1", activation_policy=AlwaysActivatePolicy())
        N2 = Node(description="N2", activation_policy=AlwaysActivatePolicy())
        N_AND = Node(description="AND", activation_policy=AndActivationPolicy())
        N3 = Node(description="N3", activation_policy=AlwaysActivatePolicy())
        END = Node(description="END", activation_policy=AlwaysActivatePolicy())
        N3.set_decomposition_factory(external_process)

        START.connect(Transition(N1))
        START.connect(Transition(N2))

        N1.connect(Transition(N_AND))
        N2.connect(Transition(N_AND))

        N_AND.connect(Transition(N3))

        N3.connect(Transition(N1, lambda workflow, node: workflow.state['foo']['bar']))
        N3.connect(Transition(END, lambda workflow, node: not workflow.state['foo']['bar']))

        queue = Queue()
        N2.set_decomposition_factory(QueueTaskDecomposition(queue)) # in practice, this is a queue name in a broker
        w = MiniWorkflow(START)
        w.run()
        assert_that(w.executed_trace, equal_to(['START', 'N1']))

        continuation = MiniWorkflow(START)
        continuation.set_state(w.get_state())
        continuation.complete_by_uuid(queue.get(), "Some external result")
        [continuation.step() for _ in range(3)]
        external_process.response = {'foo': {'bar': False}}
        [continuation.step() for _ in range(3)]
        assert_that(continuation.executed_trace, equal_to(['START', 'N1', 'N2', 'AND', 'N3', 'N1', 'AND', 'N3', 'END']))

