class TaskResult(object):
    COMPLETED = "completed"
    WAIT = "wait"


class Transition(object):
    def __init__(self, target_node, condition=None):
        self.condition = condition
        self.target_node = target_node
        self.source_node = None

    def inv_connect(self, node):
        self.source_node = node
        self.target_node.in_transitions.append(self)


    def accept(self, visitor):
        if visitor.visit_transition(self):
            self.target_node.accept(visitor)

    def eval(self, workflow, node):
        return self.condition is None or self.condition(workflow, node)


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
            if not isinstance(n, Node):
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


class WorkflowObserver(object):
    def __init__(self):
        self.notifications = {}

    def notify(self, event, data):
        print "%s node %s" % (event, data)
        self.notifications.setdefault(event, []).append(data)

    def get(self, event):
        return self.notifications.get(event, [])


def NodeIterator(workflow):
    active = workflow.active_nodes[:]
    while len(active) > 0:
        for node_uuid in active:
            node = workflow.nodes[node_uuid]
            workflow.active_nodes.remove(node_uuid)
            yield node
        active = workflow.active_nodes[:]


class MiniWorkflow(BaseVisitor):
    def collect_nodes(self, start_node):
        start_node.accept(self)

    def __init__(self, start_node, state=None):
        super(MiniWorkflow, self).__init__()
        self.state = state or {}
        self.start_node = start_node
        self.activation_trace = []
        self.waiting_trace = []
        self.waiting_list = []
        self.active_nodes = [start_node.uuid()]
        self.executed_trace = []
        self.node_iterator = NodeIterator(self)
        self.observer = WorkflowObserver()
        self.__nodes = None
        self.__state_keys = ['state', 'activation_trace', 'waiting_trace', 'executed_trace', 'waiting_list',
                             'active_nodes']

    def get_node(self):
        if self.__nodes is None:
            self.__nodes = {}
            self.collect_nodes(self.start_node)
        return self.__nodes

    nodes = property(get_node)

    def get_state(self):
        return dict([(k, getattr(self, k)) for k in
                     self.__state_keys])

    def set_state(self, s):
        for k in self.__state_keys:
            setattr(self, k, s[k])

    def _visit_node(self, node):
        self.__nodes[node.uuid()] = node

    def update_state(self, update):
        self.state.update(update)

    def has_executed(self, a_node):
        return (a_node.uuid() in self.executed_trace and
                not a_node.uuid() in self.waiting_list and
                not a_node.uuid() in self.active_nodes)


    def fetch(self, ):
        return self.node_iterator.next()

    def step(self, ):
        node = self.fetch()
        self.execute(node)

    def run(self):
        while True:
            try:
                self.step()
            except StopIteration:
                break

    def activate(self, a_node):
        self.observer.notify("activating", a_node)
        self.activation_trace.append(a_node.uuid())
        self.active_nodes.append(a_node.uuid())

    def waiting(self, node):
        self.waiting_trace.append(node.uuid())
        self.waiting_list.append(node.uuid())

    def completed(self, node):
        if node.uuid() in self.waiting_list:
            self.waiting_list.remove(node.uuid())
        self.executed_trace.append(node.uuid())
        # signal transitions
        for transition in node.out_transitions:
            if transition.eval(self, node) and transition.target_node.can_execute_in(self):
                self.activate(transition.target_node)

    def execute(self, node):
        self.observer.notify("executing", node)
        node.execute(self)

    def complete_by_uuid(self, uuid, data):
        self.nodes[uuid].complete(self, data)
        self.node_iterator = NodeIterator(self)


class Node(object):
    def __init__(self, description, activation_policy=None):
        self.activation_policy = activation_policy or AlwaysActivatePolicy()
        self.in_transitions = []
        self.out_transitions = []
        self.description = description
        self.decomposition_factory = None

    def get_digraph_node(self):
        return self.description + "\n"

    def get_digraph_rels(self):
        r = []
        for t in self.out_transitions:
            assert isinstance(t, Transition)
            r.append("%s -> %s\n" % (self.description, t.target_node.description))
        return "\n".join(r)

    def __repr__(self):
        return "<%s object at 0x%x ('%s')>" % (self.__class__.__name__, id(self), self.description)

    def accept(self, visitor):
        visitor.visit_node(self)
        for t in self.out_transitions:
            t.accept(visitor)

    def execute_transitions(self, context):
        pass

    def uuid(self):
        return self.description

    def connect(self, transition):
        self.out_transitions.append(transition)
        transition.inv_connect(self)

    def execute(self, workflow):
        if self.decomposition_factory:
            response = self.decomposition_factory.get_instance().execute(self, workflow)
        else:
            response = TaskResult.COMPLETED
        {
            TaskResult.COMPLETED: workflow.completed,
            TaskResult.WAIT: workflow.waiting
        }[response](self)


    def set_decomposition_factory(self, decomposition_factory):
        self.decomposition_factory = decomposition_factory

    def can_execute_in(self, workflow):
        return self.activation_policy.can_activate(self, workflow)

    def complete(self, workflow, data):
        self.process_async_completion(workflow, data)
        workflow.completed(self)

    def process_async_completion(self, workflow, data):
        pass


class AndActivationPolicy(object):
    """
    Wait for all previous nodes to be activated
    """

    def can_activate(self, node, workflow):
        print node, node.in_transitions
        return all(workflow.has_executed(t.source_node) for t in node.in_transitions)


class AlwaysActivatePolicy(object):
    def can_activate(self, *_):
        return True