from uuid import uuid4

__author__ = 'Juan'

class MiniWorkflowProgram(object):
    def __init__(self, node):
        self.active = {node}


#class NodeState:
#    WAITING = "waiting"
#    COMPLETE = "complete" #
#    UNKNOWN = "unknown"


class PrintDecomposition(object):
    def execute(self, node, context):
        print node.description


class Task(object):
    def __init__(self, decomposition):
        self.decomposition = decomposition

    def execute(self, node, context):
        self.decomposition.execute(node, context)
        return TaskResult.COMPLETED

        #class Node(object):

#    def __init__(self, spec):
#        self.spec = spec
#        self.state = NodeState.READY


class NotReadyException(Exception):
    pass


class TaskResult(object):
    COMPLETED = "completed"
    WAIT = "wait"


class NodeSpec(object):

    def __repr__(self):
        return "<%s '%s' at 0x%x>" % (self.__class__.__name__, self.description, id(self))

    def __init__(self, description, uuid=None):
        self.uuid = uuid or str(uuid4())
        self.out_transitions = []
        self.description = description
        self.tasks = []
        self.precondition = None

    def add_task(self, t):
        self.tasks.append(t)

    def set_condition(self, c):
        self.precondition = c

    def connect(self, transition):
        self.out_transitions.append(transition)

    def ready(self):
        return self.precondition is None or self.precondition.eval(self)

    def execute(self, ctxt):
        if not self.ready():
            raise NotReadyException
        if all(t.execute(self, ctxt) == TaskResult.COMPLETED for t in self.tasks):
            self.do_transitions(ctxt)
        else:
            ctxt.add_wait(self)

    def completed(self, ctxt):
        ctxt.completed(self)
        self.do_transitions(ctxt)

    def do_transitions(self, ctxt):
        [ctxt.activate(t.node()) for t in self.out_transitions if t.eval(self)]


class Transition(object):
    def __init__(self, condition, target_node):
        self.condition = condition
        self.target_node = target_node

    def node(self):
        return self.target_node

    def eval(self, node):
        return self.condition is None or self.condition.eval(node)


class WorkflowEvent(object):
    NODE_WAIT = "node_wait"
    NODE_EXECUTE = "node_execute"
    NODE_COMPLETED = "node_completed"


class Workflow(object):
    def __init__(self, activated_nodes, waiting, end_node, observer):
        self.activated_nodes = activated_nodes
        self.end_node = end_node
        self.waiting = waiting
        self.observer = observer

    def completed(self, node):
        self.observer.notify(WorkflowEvent.NODE_COMPLETED, node)

    def run(self):
        ready_nodes = [node for node in self.activated_nodes if self.activated_nodes[node].ready()]
        while len(ready_nodes) > 0:
            for node_uuid in ready_nodes:
                node = self.activated_nodes[node_uuid]
                del self.activated_nodes[node_uuid]
                self.observer.notify(WorkflowEvent.NODE_EXECUTE, node)
                node.execute(self)
            ready_nodes = [node for node in self.activated_nodes if self.activated_nodes[node].ready()]

    def activate(self, node):
        self.activated_nodes[str(uuid4())] = node

    def complete_by_id(self, uuid):
        self.waiting[uuid].completed(self)
        self.run()

    def add_wait(self, node):
        self.observer.notify(WorkflowEvent.NODE_WAIT, node)
        self.waiting[node.uuid] = node