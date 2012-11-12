require 'set'

class Printer
  def visit  n
    puts n.to_xml
  end

end

class Dotter
  def initialize
    @noderels = []
    @seen = Set.new
  end
  def visit  n
    if @seen.member? n
      return
    end
    @seen << n
  end
  def print_it
    nodes = ''
    arcs = ''
    @seen.each do |n|
      nodes += n.get_digraph_node
      arcs += n.get_digraph_rels
    end

    d =  "digraph Test {"
    d += nodes
    d += arcs
    d += "}"
    d
  end
end

module Digraph
  def name n
    n.to_s.delete("<#:>")
  end
  def get_digraph_node
      e = ''
      if @executed
        e = ' (executed)'
      end
      "node_#{name self} [label = \"#{name self.class}#{e}\"]\n"
  end
  def get_digraph_rels
    d = ''
    @outNodes.each do |node_to|
      d += "node_#{name self} -> node_#{name node_to}\n"
    end
    d
  end
end

module NodeToXml
  def to_xml
    s = "<node type=\"#{self.class}\" id=\"#{@node_id}\">\n"
    s += "\t<innodes>\n"
    @inNodes.each do |in_node|
      s+= "\t\t<node id=\"#{in_node.id}\"/>\n"
    end
    s += "\t</innodes>\n"
    s += "\t<outnodes>\n"
    @outNodes.each do |out_node|
      s+= "\t\t<node id=\"#{out_node.id}\"/>\n"
    end
    s += "\t</outnodes>\n"
    s+= "</node>\n"
    s+= "\n"
  end
end

class Node
  include Digraph
  include NodeToXml

  @@node_id = 0
  @@maxInNodes = 0
  @@maxOutNodes = 0
  def initialize
    super
    @inNodes = []
    @outNodes = []
    @node_id = @@node_id
    @@node_id += 1
    @executed = false
  end
  def executed
    @executed
  end
  def id
    @node_id
  end
  def addInNode node
    @inNodes << node
  end
  def addOutNode node
    @outNodes << node
  end
  def accept visitor
    visitor.visit self
    @outNodes.each do |on|
      on.accept visitor
    end
  end
  def out_nodes
    @outNodes
  end
  def execute workflow
    @executed = true
  end
end
class ParallelSplitNode < Node
  @@maxInNodes = 1
  @@maxOutNodes = -1
  def execute workflow
    super
    @outNodes.each do |n|
      workflow.activate n
    end
  end
end


class StartNode < Node
  @@maxInNodes = 0
  @@maxOutNodes = 1
  def execute workflow
    super
    workflow.activate @outNodes.first
  end
end

class EndNode < Node
  @@maxInNodes = 1
  @@maxOutNodes = 0
  def execute workflow
    super
    puts "the end"
  end
end

class ActionNode < Node
  def initialize
    super
  end
  def action=(o)
    @action = o
  end
  def action
    @action
  end
  def execute workflow
    super
    @action.run
    workflow.activate @outNodes.first
  end
  def get_digraph_node
      e = ''
      if @executed
        e = ' (executed)'
      end
      "node_#{name self} [label = \"#{name self.class} - '#{@action.to_s}' - #{e}\"]\n"
  end
end

class SubWorkflowNode < Node
end

class WorkflowExecution
  def initialize
    super
    @startNode = nil
    @nodes = []
    @activated_nodes = Hash.new
    #@waiting_execution = Hash.new
    @num_of_activated_nodes = 0
    @num_of_activated_end_nodes = 0

    @cancelled = false
    @ended = false
    @workflow_state = Hash.new
    @workflow_instance = nil
  end
  def ended
    @activated_nodes.empty?
  end
  def activate n
    if n.class == EndNode
      @activated_nodes[n] = n
    else
      @activated_nodes[n] = n
    end
  end
  def start_node=(n)
    @startNode = n
    @activated_nodes[n] = n
  end

  def activated_nodes
    @activated_nodes
  end

  def resume
  end
  def execute
    begin
      executed = false
      @activated_nodes.values.each do |activated_node|
        if @canceled or @ended
          break
        end
        #if not (activated_node.class == EndNode and @num_of_activated_nodes != @num_of_activated_end_nodes)
          if activated_node.execute(self)
            executed = true
            @activated_nodes.delete activated_node
            @num_of_activated_nodes -= 1
          elsif activated_node.class == InputNode
              # create task for user
              # task = @workflow_instance.new_task(activated_node.role)
              # task.add_input
          end
        #end
      end
    end while not @activated_nodes.empty? and executed
    if not @cancelled and not ended
      puts @activated_nodes.keys
      puts "suspended"
    end
  end
  def set_value( k, v)
    @workflow_state[k] = v
  end
  def state
    @workflow_state
  end
  def accept visitor
    @startNode.accept visitor
  end
end

#wkf = WorkflowExecution.new
#
#sn = StartNode.new
#
#class SetVariableNode < Node
#  @@maxInNodes = 1
#  @@maxOutNodes = 1
#  def initialize(varname)
#    super
#    @varname = varname
#  end
#  def varname
#    @varname
#  end
#end
#
#class InputNode < Node
#  @@maxInNodes = 1
#  @@maxOutNodes = 1
#  def initialize message, k
#    super()
#    @variable_name = k
#    @message = message
#    @roles = []
#  end
#  def add_input
#  end
#  def add_role role
#    @roles << role
#  end
#  def is_data_ready
#  end
#  def execute workflow
#    super
#    puts @message
#    value = gets.strip
#    workflow.set_value(@variable_name, value)
#    workflow.activate @outNodes.first
#  end
#end
#
#class Condition
#  def initialize(value_name_to_check, value_to_check_against)
#    @v = value_name_to_check
#    @c = value_to_check_against
#  end
#  def check workflow
#    workflow.state[@v] == @c
#  end
#  def to_s
#    "condition #{@v} == #{@c}"
#  end
#end
#
#class SimpleBranchNode < Node
#  @@maxInNodes = 1
#  @@maxOutNodes = -1
#  def initialize
#    super()
#    @conditions = Hash.new
#  end
#  def addOutNode(node, condition)
#    super(node)
#    @conditions[condition] = node
#  end
#  def execute workflow
#    super
#    @conditions.keys.each do |condition|
#      if condition.check workflow 
#        workflow.activate @conditions[condition]
#        break
#      end
#    end
#    true
#  end
#  def get_digraph_rels
#    d = ''
#    @conditions.keys.each do |condition|
#      node_to = @conditions[condition]
#      d += "node_#{name self} -> node_#{name node_to} [label = \"#{condition.to_s}\"]\n"
#    end
#    d
#  end
#end
#
#class Greater
#  def initialize message
#    @m = message
#  end
#  def run
#    puts @m
#  end
#  def to_s
#    "prints #{@m}"
#  end
#end
#class UnconditionalMerge < Node
#  @@maxInNodes = -1
#  @@maxOutNodes = 1
#  def execute workflow
#    super
#    workflow.activate @outNodes.first
#  end
#end
#
#an = ActionNode.new 
#an.action = Greater.new "Hola"
#
#en = EndNode.new
#merge = UnconditionalMerge.new
#
#input_node = InputNode.new "Please enter either 'foo' or 'bar'. The value will be saved in 'testing'", "testing"
## assembly the wkf
#
#conditional = SimpleBranchNode.new
#
#si = ActionNode.new
#si.action = Greater.new "si"
#no = ActionNode.new
#no.action = Greater.new "no"
#conditional.addOutNode si, Condition.new("testing", "foo")
#conditional.addOutNode no, Condition.new("testing", "bar")
#
#si.addInNode conditional
#no.addInNode conditional
#
#si.addOutNode merge
#no.addOutNode merge
#
#merge.addInNode si
#merge.addInNode no
#
#sn.addOutNode an
#an.addInNode sn
#an.addOutNode input_node
#
#input_node.addInNode an
#input_node.addOutNode conditional
#
#split = ParallelSplitNode .new
#
#a = ActionNode.new
#b = ActionNode.new
#a.action = Greater.new "a"
#b.action = Greater.new "b"
#
#split.addInNode merge
#
#split.addOutNode a
#split.addOutNode b
#
#
#merge2 = UnconditionalMerge.new
#a.addOutNode merge2
#b.addOutNode merge2
#
#merge2.addInNode a
#merge2.addInNode b
#
#merge2.addOutNode en
#
#merge.addOutNode split
#en.addInNode merge2
#
#wkf.start_node = sn
#
#def dump_diagram workflow, filename
#  dotter = Dotter.new
#  workflow.accept dotter
#  dot = File.new(filename, "w")
#  dot.write(dotter.print_it)
#  dot.close
#
#end
#
#dump_diagram wkf, "diagram.dot"
#puts "\n"
#puts "You can use dotty to check the diagram for the following workflow running 'dotty diagram.dot'\n"
#
#wkf.execute
#
#puts "Workflow ended with variable values:"
#
#wkf.state.keys.each do |k|
#  puts "#{k} -> #{wkf.state[k]}\n"
#end
#
##sn.accept Printer.new
#dump_diagram wkf, "diagram_executed.dot"
