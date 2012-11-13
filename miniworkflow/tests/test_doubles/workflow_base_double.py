from miniworkflow import WorkflowNotFound

class WorkflowBaseDouble(object):
    def __init__(self, workflow_dict):
        self.workflow_dict = workflow_dict

    def get_workflow(self, workflow_id):
        try:
            return self.workflow_dict[workflow_id]
        except KeyError:
            raise WorkflowNotFound(workflow_id)

    def add_workflow(self, workflow_id, w):
        self.workflow_dict[workflow_id] = w