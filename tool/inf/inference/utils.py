import ast
import _ast

def walk_flat(node):
  pass

def node_to_str(node):
    if hasattr(node, 'lineno'):
        return str(node.lineno)+' '+str(node)
    else:
        return str(node)