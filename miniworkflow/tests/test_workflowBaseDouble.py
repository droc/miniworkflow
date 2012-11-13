from unittest import TestCase
from miniworkflow.tests.test_interfaces.test_workflowBaseInterface import WorkflowBaseInterfaceTest
from miniworkflow.tests.test_workflowEngine import WorkflowBaseDouble


class TestWorkflowBaseDouble(TestCase, WorkflowBaseInterfaceTest):
    def setUp(self):
        self.object = WorkflowBaseDouble({})

