from uuid import uuid4

__author__ = 'Juan'

class MiniWorkflowProgram(object):
    def __init__(self, node):
        self.active = set([node])


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
    def get_digraph_node(self):
        return "node_%s [label = \"%s\"]\n" % (self.description, self.description)

    def get_digraph_rels(self):
        d = ''
        for transition in self.out_transitions:
            d += "node_%s -> node_%s\n" % (self.description, transition.target_node.description)
        return d

    def __repr__(self):
        return "<%s '%s' at 0x%x>" % (self.__class__.__name__, self.description, id(self))

    def accept(self, visitor):
        visitor.visit_node(self)
        for t in self.out_transitions:
            t.accept(visitor)

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
        return (self.precondition is None or self.precondition.eval(self)) and self.specialized_ready()

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
        [t.take(self) for t in self.out_transitions]

    def specialized_ready(self):
        return True


class AndNode(NodeSpec):
    def specialized_ready(self):
        return self.all_in_transitions_taken()

    def all_in_transitions_taken(self):
        pass


class Transition(object):
    def __init__(self, target_node, condition=None):
        self.condition = condition
        self.target_node = target_node
        self.source_node = None

    def inv_connect(self, node):
        self.source_node = node

    def take(self, n):
        if self.eval(n):
            self.target_node.activate()

    def accept(self, visitor):
        if visitor.visit_transition(self):
            self.target_node.accept(visitor)

    def node(self):
        return self.target_node

    def eval(self, node):
        return self.condition is None or self.condition.eval(node)


class BaseVisitor(object):
    def __init__(self):
        self.visited = set()

    def visit_transition(self, t):
        if not t in self.visited:
            self.visited.add(t)
            self._visit_transition(t)
            return True
        return False

    def visit_node(self, n):
        if not n in self.visited:
            self.visited.add(n)
            self._visit_node(n)
            return True
        return False

    def _visit_transition(self, t):
        pass

    def _visit_node(self, n):
        pass


class DotVisitor(BaseVisitor):
    def _visit_transition(self, t):
        print t

    def _visit_node(self, n):
        print n

    def print_it(self):
        nodes = []
        arcs = []
        for n in self.visited:
            if not isinstance(n, NodeSpec):
                continue
            nodes.append(n.get_digraph_node())
            arcs.append(n.get_digraph_rels())

        d = "digraph Test {"
        d += " graph [rankdir = LR];"
        d += "".join(nodes)
        d += "".join(arcs)
        d += "}"
        return d


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