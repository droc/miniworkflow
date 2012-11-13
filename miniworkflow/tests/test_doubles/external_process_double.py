from miniworkflow import TaskResult

class ExternalProcessDouble(object):
    def __init__(self):
        self.response = {}

    def get_instance(self):
        return self

    def execute(self, _, workflow):
        workflow.update_workflow_variables(self.response)
        return TaskResult.COMPLETED