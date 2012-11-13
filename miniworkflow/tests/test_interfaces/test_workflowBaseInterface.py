from hamcrest import assert_that
from hamcrest_matchers import responds_to

class WorkflowBaseInterfaceTest:
    def test_responds_to_get_workflow(self):
        #noinspection PyUnresolvedReferences
        assert_that(self.object, responds_to("get_workflow"))

    def test_responds_to_add_workflow(self):
        #noinspection PyUnresolvedReferences
        assert_that(self.object, responds_to("add_workflow"))