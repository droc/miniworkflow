from unittest import TestCase
from miniworkflow.tests.test_doubles.workflow_base_double import WorkflowBaseDouble
from miniworkflow.tests.test_interfaces.test_workflowBaseInterface import WorkflowBaseInterfaceTest


class TestWorkflowBaseDouble(TestCase, WorkflowBaseInterfaceTest):
    def setUp(self):
        self.object = WorkflowBaseDouble({})

