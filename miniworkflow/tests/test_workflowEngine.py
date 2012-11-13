from Queue import Queue
from StringIO import StringIO
from unittest import TestCase
from hamcrest import assert_that, equal_to, has_length, has_item, is_not, starts_with
from miniworkflow import Transition, MiniWorkflow, Node, AndActivationPolicy, AlwaysActivatePolicy, \
    WorkflowFactory, EventProcessor, EmailReceivedEvent, WaitForExternalEvent
from miniworkflow.decomposition import QueueTaskDecomposition
from miniworkflow.tests.test_doubles.external_process_double import ExternalProcessDouble
from miniworkflow.tests.test_doubles.workflow_base_double import WorkflowBaseDouble


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
        get_target_os.connect(Transition(target_node=reopen_os_ticket, condition=lambda *_: False))
        reopen_os_ticket.connect(Transition(target_node=wait_for_target_mail))

        get_imp.connect(Transition(target_node=gen_test_case))

        gen_test_case.connect(Transition(end))

        #        visitor = DotVisitor()
        #        start.accept(visitor)
        #        with open("graph.dot", 'w') as f:
        #            f.write(visitor.print_it())
        w = MiniWorkflow(start)
        w.run(50)
        assert_that(w.executed_trace, equal_to(
            ['start', 'wait_for_imp_mail', 'wait_for_target_mail', 'get_imp', 'get_target_os', 'gen_test_cases',
             'end']))
    def test_gives_a_graph_representation_of_itself(self):
        start = self.build_workflow_def()
        g = StringIO()
        start.write_graph(g)
        assert_that(g.getvalue(), starts_with("digraph Test"))

    def build_workflow_def(self):
        self.external_process_double = ExternalProcessDouble()
        self.external_process_double.response = {'foo': {'bar': True}}
        START = Node(description="START", activation_policy=AlwaysActivatePolicy())
        N1 = Node(description="N1", activation_policy=AlwaysActivatePolicy())
        N2 = Node(description="N2", activation_policy=AlwaysActivatePolicy())
        N_AND = Node(description="AND", activation_policy=AndActivationPolicy())
        N3 = Node(description="N3", activation_policy=AlwaysActivatePolicy())
        END = Node(description="END", activation_policy=AlwaysActivatePolicy())
        N3.set_decomposition_factory(self.external_process_double)
        START.connect(Transition(N1))
        START.connect(Transition(N2))
        N1.connect(Transition(N_AND))
        N2.connect(Transition(N_AND))
        N_AND.connect(Transition(N3))
        N3.connect(Transition(N1, lambda workflow, node: workflow.workflow_variables['foo']['bar']))
        N3.connect(Transition(END, lambda workflow, node: not workflow.workflow_variables['foo']['bar']))
        self.queue_tasks_N2 = Queue()
        N2.set_decomposition_factory(
            QueueTaskDecomposition(self.queue_tasks_N2)) # in practice, this is a queue name in a broker
        return START

    def test_conditional_loop(self):
        START = self.build_workflow_def()

        w = MiniWorkflow(START)
        #w.observer.subscribe(WorkflowEvent.NODE_EXECUTE, WorkflowEventPublisher("workflow_ticketing"))
        w.run()
        assert_that(w.executed_trace, equal_to(['START', 'N1']))

        continuation = MiniWorkflow(START)
        #continuation.observer.subscribe(WorkflowEvent.NODE_EXECUTE, WorkflowEventPublisher("workflow_ticketing"))
        continuation.set_state(w.get_state())
        continuation.complete_by_uuid(self.queue_tasks_N2.get(), "Some external result")
        [continuation.step() for _ in range(3)]
        self.external_process_double.response = {'foo': {'bar': False}}
        [continuation.step() for _ in range(3)]
        assert_that(continuation.executed_trace, equal_to(['START', 'N1', 'N2', 'AND', 'N3', 'N1', 'AND', 'N3', 'END']))

    def get_gen_test_cases_example_def(self):
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
        wait_for_target_mail.set_decomposition_factory(WaitForExternalEvent())
        get_target_os.connect(Transition(target_node=gen_test_case))
        get_target_os.connect(Transition(target_node=reopen_os_ticket, condition=lambda *_: False))
        reopen_os_ticket.connect(Transition(target_node=wait_for_target_mail))
        get_imp.connect(Transition(target_node=gen_test_case))
        gen_test_case.connect(Transition(end))
        return start

    def test_processor_resumes_workflow_with_email(self):
        workflow_def = self.get_gen_test_cases_example_def()

        WORKFLOW_ID = 1
        WORKFLOW_ID2 = 2

        w1 = MiniWorkflow(workflow_def)
        w2 = MiniWorkflow(workflow_def)
        w1.run()
        w2.run()
        workflow_base = WorkflowBaseDouble({
            WORKFLOW_ID: w1,
            WORKFLOW_ID2: w2
        })
        assert_that(w1.executed_trace, is_not(has_item('wait_for_target_mail')))
        workflow_factory = WorkflowFactory(workflow_def)
        event_processor = EventProcessor(workflow_base, workflow_factory)
        event_processor.process(EmailReceivedEvent(WORKFLOW_ID, 'wait_for_target_mail'))
        assert_that(w1.executed_trace, has_item('wait_for_target_mail'))

    def test_processor_creates_instance_if_none_exists(self):
        workflow_def = self.get_gen_test_cases_example_def()
        WORKFLOW_ID = 1
        workflow_base = WorkflowBaseDouble({})
        workflow_factory = WorkflowFactory(workflow_def)
        event_processor = EventProcessor(workflow_base, workflow_factory)
        event_processor.process(EmailReceivedEvent(WORKFLOW_ID, 'wait_for_target_mail'))
        assert_that(workflow_base.get_workflow(WORKFLOW_ID).executed_trace, has_item('wait_for_target_mail'))
