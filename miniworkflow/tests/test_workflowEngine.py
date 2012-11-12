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


class NewWorkflow(object):
    def __init__(self, start_node, state=None, active_nodes=None):
        self.state = state or {}
        self.start_node = start_node
        self.activation_trace = []
        self.waiting_trace = []
        self.completed_trace = []
        self.active_nodes = not active_nodes is None and active_nodes or {}
        self.executed_trace = []

    def has_executed(self, a_node):
        return (a_node.uuid() in self.executed_trace and
                not a_node.uuid() in self.waiting_trace and
                not a_node.uuid() in self.activation_trace)

    def run(self):
        active = self.active_nodes.copy()
        while len(active) > 0:
            for node_uuid in active:
                node = active[node_uuid]
                del self.active_nodes[node_uuid]
                self.execute(node)
            active = self.active_nodes.copy()

    def activate(self, start_node):
        self.activation_trace.append(start_node)
        self.active_nodes[start_node.uuid()] = start_node

    def waiting(self, node):
        self.waiting_trace[node.uuid()] = node

    def completed(self, node):
        self.executed_trace.append(node.uuid())

    def execute(self, node):
        node.execute(self)


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

    def test_and_node_and_loop(self):
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

    def test_foo(self):
        class Node(object):
            def __init__(self, description, activation_policy):
                self.activation_policy = activation_policy
                self.in_transitions = []
                self.out_transitions = []
                self.description = description
                self.decomposition_factory = None

            def uuid(self):
                return self.description

            def connect(self, node):
                self.out_transitions.append(node)
                node.inv_connect(self)

            def execute(self, workflow):
                if self.decomposition_factory:
                    response = self.decomposition_factory.get_instance().execute(self, workflow)
                else:
                    response = TaskResult.COMPLETED
                {
                    TaskResult.COMPLETED : workflow.completed,
                    TaskResult.WAIT: workflow.waiting
                }[response](self)


            def set_decomposition_factory(self, decomposition_factory):
                self.decomposition_factory = decomposition_factory

            def can_execute_in(self, workflow):
                return self.activation_policy.can_activate(self, workflow)

        class ExternalProcessDouble(object):
            def __init__(self):
                self.response = None

        class ExternalProcessFactory(object):
            def __init__(self, instance):
                self.instance = instance

            def get_instance(self):
                return self.instance

        class AndActivationPolicy(object):
            """
            Wait for all previous nodes to be activated
            """

            def can_activate(self, node, workflow):
                return

        class AlwaysActivatePolicy(object):
            def can_activate(self, *_):
                return True

        external_process = ExternalProcessDouble()
        START = Node(description="START", activation_policy=AlwaysActivatePolicy())
        N1 = Node(description="N1", activation_policy=AlwaysActivatePolicy())
        N2 = Node(description="N2", activation_policy=AlwaysActivatePolicy())
        N_AND = Node(description="AND", activation_policy=AndActivationPolicy())
        N3 = Node(description="N3", activation_policy=AlwaysActivatePolicy())
        END = Node(description="END", activation_policy=AlwaysActivatePolicy())
        N3.set_decomposition_factory(ExternalProcessFactory(external_process))

        START.connect(Transition(N1))
        START.connect(Transition(N2))

        N1.connect(Transition(N_AND))
        N2.connect(Transition(N_AND))

        N_AND.connect(Transition(N3))

        N3.connect(Transition(N1, lambda ctxt: ctxt.state['foo']['bar']))
        N3.connect(Transition(END))

        w = NewWorkflow(START, active_nodes={START.uuid(): START})
        w.run()
        assert_that(w.has_executed(START))
        assert_that(w.has_executed(N1))
        assert_that(w.has_executed(N2))

