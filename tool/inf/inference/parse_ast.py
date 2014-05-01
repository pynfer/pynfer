import ast
import os
from inf.inference.typez import (
        Typez,
        Scope,
        none_type,
        any_type,
        is_none
        )
import inf.inference.typez as typez
from inf.inference.log import logger
import inf.parsing.utils as utils

def safe_resolve(obj, attrs):
    try:
        for attr in attrs.split('.'):
            obj = getattr(obj, attr)
        return obj
    except Exception:
        return None

def not_none(*args):
    for arg in args:
        if arg != None:
            return arg
   
"""
We resolve types of individual variables by symbolic execution of the code.
"""

def logentry(fn):
    """decorator for logging visit of a node"""
    def _f(*args):
        node = [_node for _node in args if isinstance(_node, ast.AST)][0]
        if hasattr(node, 'lineno'):
            line = str(node.lineno)
        else:
            line = '?'
        logger.debug(line + " "+fn.__name__)
        return fn(*args)
    _f.__name__ = fn.__name__
    return _f


class ReturnException(Exception):

    def __init__(self, res):
        self.res=res

class RaiseException(Exception):

    def __init__(self, res, statement=None):
        self.res=res
        self.statement=statement
        
class BreakException(Exception):
    pass

class SuperBreakException(Exception):
    pass

class Problem:
    """encapsulates data about execution problem, that may occur (such as unknown attribute)"""
    def __init__(self, node = None, message = None, symbol = None):
        self.node = node
        self.message = message
        self.symbol = symbol

    def __str__(self):
        return "Problem(message: %s, symbol: %s, node: %s, line: %d)"%(self.message, str(self.symbol),
                str(self.node.__class__), self.node.lineno)

    def __repr__(self):
        return self.__str__()
        
    def __eq__(self, other):
        return self.__dict__ == other.__dict__ 
        

class Parser:
    """
class that gathers parsing utilites.

attributes:
modules: TODO. will be list of modules already imported
problems: list of all problems found by parsing
visited_ast_nodes:

main parser method is eval_code. exec_* methods are used to process individual ast nodes.
"""
    def __init__(self,extern_scope=None):
        self.specials = {}
        self.modules = []
        self.problems = []
        self.visited_ast_nodes=[]
        self.breakpoint = None
        
        if extern_scope is None:
            #f = open("inf/inference/externs.py", "r")
            curr_location = os.path.dirname(os.path.realpath(__file__))
            f = open(curr_location+'/externs.py', 'r')
            source = f.read()
            f.close()
            node = ast.parse(source, filename = 'externs.py', mode = 'exec')
            logger.info('parsing externs')
            self.extern_scope = Scope(is_root = True)
            self.root_scope = Scope(parent = self.extern_scope)
            self.eval_code(node, self.extern_scope)
            logger.info('!!!externs parsed')
            #print('externs parsed')
        else:
            self.extern_scope = extern_scope
            self.root_scope = Scope(parent = self.extern_scope)
        
        self.modules = []
        self.problems = []

    def warn(self, node = None, message = None, symbol = None):
        """add new problem"""
        self.problems.append(Problem(node, message, symbol))
    
    
    def _exec_Assign(self,lhs,rhs,node,scope,evalR=True):
        '''
        This method distributes job on more specific methods according to the kind of the left side
        arguments:
        lhs : left hand side of assignment
        rhs : right hand side of assigment
        node : according AST node of assignement
        evalR: optional arg whether is needed to evaluate rhs arg (False when rhs is already Typez object - tuple case)
        '''
        if isinstance(rhs, ast.Name) and evalR:
            rhs_type = self.eval_code(rhs,scope)
            #if rhs_type is None:
            #    self.warn(node, "NameError: Name '"+ rhs.id + "' is not defined", rhs.id)
        if isinstance(lhs, ast.Name):
            self._exec_Name_Assign(lhs, rhs,node,scope,evalR)
        elif isinstance(lhs, ast.Attribute):
            self._exec_Attr_Assign(lhs, rhs,node,scope,evalR)
        elif isinstance(lhs, ast.Subscript):
            self._exec_Subscript_Assign(lhs, rhs,node,scope,evalR)
        elif isinstance(lhs, ast.Tuple):
            self._exec_Tuple_Assign(lhs, rhs,node,scope,evalR)
            #pass
        else:
            raise Exception('should not get here')
    
    def _exec_Name_Assign(self,lhs,rhs,node,scope,evalR):
        '''
        Method that executes assigment to Name
        args same as _exec_Assign
        '''
        lhs_val = self.eval_code(lhs, scope)
        if hasattr(lhs_val, 'kind') and lhs_val.kind=='const':
            self.warn(node, "can't assign to literal", lhs.id)
        if evalR:
            name_type = self.eval_code(rhs,scope)
        else:
            name_type = rhs            
        if hasattr(name_type, 'kind') and name_type.kind=='const':
            name_type_clone = name_type.clone()
            name_type_clone.kind='obj'
            scope[lhs.id] = name_type_clone
        else:
            scope[lhs.id] = name_type
    
    def _exec_Attr_Assign(self,lhs,rhs,node,scope,evalR):
        '''
        Method responsible for cases when attribute is on the left side (x.y.z = 5)
        '''
        if isinstance(lhs.ctx, ast.Store):
            lhs_obj = self.eval_code(lhs.value, scope)
            if lhs_obj is None:
                #self.warn(node, "NameError: Name '"+ lhs.value.id + "' is not defined", lhs.value.id)
                lhs_obj = any_type
            else:
                if evalR:
                    rhs_val = self.eval_code(rhs, scope)
                else:
                    rhs_val = rhs
                if rhs_val is None:
                    rhs_val = any_type
                __setattr__ = lhs_obj.resolve('__setattr__', 'class')
                if hasattr(rhs_val, 'kind') and rhs_val.kind=='const':
                    rhs_val_clone = rhs_val.clone()
                    rhs_val_clone.kind='obj'
                    args = (lhs_obj, lhs.attr, rhs_val_clone)
                else:
                    args = (lhs_obj, lhs.attr, rhs_val)
                self._exec_fun(__setattr__, args, {}, scope, node=node)
        else:
            raise Exception('bad context')
    
    def _exec_Subscript_Assign(self,lhs,rhs,node,scope,evalR):
        '''
        This methods covers cases like a[1]=1
        '''
        structure = self.eval_code(lhs.value, scope)
        if evalR:
            rhs_obj = self.eval_code(rhs,scope)
        else:
            rhs_obj = rhs
        fun_type = structure.resolve('__setitem__','class')
        if isinstance(lhs.slice, ast.Slice):
            key = self.eval_code(lhs.slice, scope)
        else:
            key = self.eval_code(lhs.slice.value, scope)
        args = [structure, key ,rhs_obj] 
        if fun_type:
            self._exec_fun(fun_type, args, {}, scope, node=node)
        else:
            self.warn(node, "object %s doesnt support indexing"%(lhs.value.id), lhs.value.id)
        
    def _exec_Tuple_Assign(self,lhs,rhs,node,scope,evalR):
        '''
        This method covers cases like a,b = x
        '''
        if evalR:
            rhs_type = self.eval_code(rhs,scope)
        else:
            rhs_type = rhs
        fun_iter = rhs_type.resolve('__iter__','class')
        if fun_iter:
            isTuple = rhs_type.resolve_class(self.extern_scope['inf_tuple'])
            if isTuple:
                stop = False
                for index,e in enumerate(lhs.elts):
                    if stop:
                        self._exec_Assign(e,any_type,node,scope,evalR=False)
                    else:
                        key = Typez(kind='const', value = index, __class__ = self.extern_scope['num'])
                        getItem = rhs_type.resolve('__getitem__','class')
                        item = self._exec_fun(getItem, [rhs_type,key], {}, scope, node=node)
                        if not item.resolve_class(self.extern_scope['PlaceHolder']):
                            self._exec_Assign(e,item,node,scope,evalR=False)
                        else:
                            stop = True
                            self._exec_Assign(e,any_type,node,scope,evalR=False)
                            self.warn(node, 'Need more than %d values to unpack'%(index), 'tuple')
                if index+1<5:
                    key = Typez(kind='const', value = index+1, __class__ = self.extern_scope['num'])
                    getItem = rhs_type.resolve('__getitem__','class')
                    item = self._exec_fun(getItem, [rhs_type,key], {}, scope, node=node)
                    if not item.resolve_class(self.extern_scope['PlaceHolder']):
                        #nerozbalili sa vsetky hodnoty co boli v tuple, malo var na lavej strane
                        self.warn(node, 'too many values to unpack (expected %d)'%(len(lhs.elts)),'tuple')
            else:
                args = [rhs_type]
                iterator = self._exec_fun(fun_iter, args, {}, scope, node=node)
                fun_next = iterator.resolve('__next__','class')
                if fun_next:
                    value = self._exec_fun(fun_next, [iterator], {}, scope, node=node)
                    for e in lhs.elts:
                        self._exec_Assign(e,value,node,scope,evalR=False)
                else:
                    self.warn(node=node,mes="does not support __next__ method",symbol="Iterator")
        else:
            if hasattr(rhs, 'id'):
                self.warn(node,"object is not iterable", rhs.id)
            else:
                symbol = hrs_type.scope['__class__'].node.name
                self.warn(node,"object is not iterable", symbol)
    
    @logentry
    def exec_Assign(self,node,scope):
        '''
        This method executes assign for each target on the left side
        '''
        for lhs in node.targets:
            self._exec_Assign(lhs, node.value,node,scope)
    
    #TODO lepsie pre vsetky moznosti targetu, ako v assign
    @logentry
    def exec_AugAssign(self, node, scope):
        '''
        This method is responsible for executing augmentation assignment like a += 1,a[1] += 1, etc.
        Only the minimum amount of work is done here, the rest is delegated to _exec_Assign method.
        '''
        op_dict = {ast.Add: '__add__',
                ast.Div: '__div__',
                ast.Mult: '__mul__',
                ast.Sub: '__sub__',
                ast.FloorDiv:'__floordiv',
                ast.Mod:'__mod__',
                ast.Pow:'__pow__',
                ast.LShift:'__lshift__',
                ast.RShift:'__rshift__',
                ast.BitOr:'or_',
                ast.BitXor:'__xor__',
                ast.BitAnd:'and_'
                }
        target = self.eval_code(node.target, scope)
        value = self.eval_code(node.value, scope)
        args = [target, value]
        
        #if isinstance(node.value, ast.Name):
        #    if value is None:
        #        self.warn(node, "NameError: Name '"+ node.value.id + "' is not defined", node.value.id)

        op_class = node.op.__class__
        if not op_class in op_dict:
            raise Exception('unknown augassign operation '+str(node.op))
        fun_type = target.resolve(op_dict[node.op.__class__],'class')
        if fun_type is None:
            res = any_type
            self.warn(node, message = 'non-existent function', symbol = op_dict[node.op.__class__])
        else:
            res = self._exec_fun(fun_type, args, {}, scope, node=node)
        self._exec_Assign(node.target, res, node, scope, False)

    @logentry
    def exec_UnaryOp(self, node, scope):
        '''
        This methods executes unary operation called, if unary op is not implemented for given operand, error is reported.
        "Not" is a keyword in Python and is called as a function with operand as an argument
        '''
        op_dict = {ast.UAdd: '__pos__',
                ast.USub: '__neg__',
                ast.Not: '__not__',
                ast.Invert: '__invert__'
                }
        op_dict_keyword = {ast.Not: '__not__'}
        
        arg = self.eval_code(node.operand, scope)
        op_class = node.op.__class__
        if not op_class in op_dict:
            raise Exception('unknown operation '+str(node.op))
        if op_class in op_dict_keyword:
            fun_type = self.extern_scope[op_dict[node.op.__class__]]
        else:
            fun_type = arg.resolve(op_dict[node.op.__class__],'class')
        if fun_type is None:
            res = any_type
            self.warn(node, message = 'non-existent function', symbol = op_dict[node.op.__class__])
        else:
            res = self._exec_fun(fun_type, [arg], {}, scope, node=node)
        return res
        
        
    @logentry
    def exec_BoolOp(self, node, scope):
        '''
        Method executes boolean operations (and,or) are not called on operands. This functions are called with operands as args.
        Example: __and__(x,y).
        '''
        op_dict = {ast.And: '__and__',
                ast.Or: '__or__',
                }
        fun_type = self.extern_scope[op_dict[node.op.__class__]]
        res = None
        values_length = len(node.values)
        for i,value in enumerate(node.values):
            if i==0:
                continue
            if res is None:
                arg1 = self.eval_code(node.values[i-1], scope)
            else:
                arg1=res
            arg2 = self.eval_code(node.values[i], scope)
            args = [arg1, arg2]
            op_class = node.op.__class__
            if not op_class in op_dict:
                raise Exception('unknown operation '+str(node.op))
            if fun_type is None:
                res = any_type
                self.warn(node, message = 'non-existent function', symbol = op_dict[node.op.__class__])
            else:
                res = self._exec_fun(fun_type, args, {}, scope, node=node)

        return res
        
    @logentry
    def exec_BinOp(self, node, scope):
        '''
        This method is responsible for executing binary operations with in the given AST.
        Binary operation is resolved on the left operand. 
        '''
        op_dict = {ast.Add: '__add__',
                ast.Div: '__div__',
                ast.Mult: '__mul__',
                ast.Sub: '__sub__',
                ast.FloorDiv:'__floordiv',
                ast.Mod:'__mod__',
                ast.Pow:'__pow__',
                ast.LShift:'__lshift__',
                ast.RShift:'__rshift__',
                ast.BitOr:'or_',
                ast.BitXor:'__xor__',
                ast.BitAnd:'and_'
                }
        left_type = self.eval_code(node.left, scope)
        right_type = self.eval_code(node.right, scope)
        args = [left_type, right_type]
        op_class = node.op.__class__
        if not op_class in op_dict:
            raise Exception('unknown operation '+str(node.op))
        fun_type = left_type.resolve(op_dict[node.op.__class__],'class')
        if fun_type is None:
            res = any_type
            self.warn(node, message = 'non-existent function', symbol = op_dict[node.op.__class__])
        else:
            res = self._exec_fun(fun_type, args, {}, scope, node=node)
        return res
        
    @logentry
    def exec_Compare(self,node,scope):
        '''
        This method executes comparison statements like: ==,<,> etc.
        Operations in comp_dict are resovelve on the left operand.
        Operation (is, is not) are considered as is(a,b). Definitions are in externs
        '''
        comp_dict = {ast.Eq: '__eq__',
                ast.NotEq: '__ne__',
                ast.Lt: '__lt__',
                ast.LtE: '__le__',
                ast.Gt: '__gt__',
                ast.GtE: '__ge__',
                ast.In: '__contains__',
                ast.NotIn: '__contains__',
                ast.Is: 'inf_is',
                ast.IsNot: 'inf_isnot'}
        
        #these are called from obj - obj.__is__()
        comp_dict_keyword = {ast.Is: 'inf_is',
                ast.IsNot: 'inf_isnot'}
        
        left_type = self.eval_code(node.left, scope)
        right_type = self.eval_code(node.comparators[0], scope)
        comp_type = comp_dict[node.ops[0].__class__]
        
        if node.ops[0].__class__ in comp_dict_keyword:
            fun_type = self.extern_scope[comp_dict_keyword[node.ops[0].__class__]]
        else:
            fun_type = left_type.resolve(comp_dict[node.ops[0].__class__],'class')
        
        comparators = self.eval_code(node.comparators[0], scope)
        args = [left_type, comparators]
        op_class = node.ops[0].__class__
        if not op_class in comp_dict:
            raise Exception('unknown operation '+str(node.ops))
        
        if fun_type is None:
            res = any_type
            self.warn(node, message = 'non-existent function', symbol = comp_dict[node.ops[0].__class__])
        else:
            res =  self._exec_fun(fun_type, args, {}, scope, node=node)
        return res
    
    @logentry
    def exec_For(self, node, scope):
        '''
        Method that executes construction of for-cycle
        The node.iter is evaluted only because of error detection inside of it.
        The body of cycle is executed only once.
        '''
        scope[node.target.id]= any_type
        range_eval = self.eval_code(node.iter, scope)
        try:
            for item in node.body:
                self.eval_code(item, scope)
        except BreakException:
            pass
    
    @logentry
    def exec_While(self, node, scope):
        '''
        Method that executes construction of while-cycle.
        The condition node.test is evaluted only because of error detection inside of it.
        The body of cycle is executed only once.
        '''
        test = self.eval_code(node.test, scope)
        try:
            for item in node.body:
                self.eval_code(item, scope)
        except BreakException:
            pass
        
    @logentry
    def exec_FunctionDef(self, node, scope):
        '''
        This method executes the definition of function. In this case, just the name of function is stored. If the docstring is included inside of definition,
        it is stored in within the corresponding Typez under attribute docstring.
        '''
        scope[node.name] = Typez(kind='funcdef', node = node, scope = scope)
        if isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Str):
            scope[node.name].docstring = node.body[0].value.s
        

    @logentry
    def exec_ClassDef(self, node, scope):
        '''
        Method that executes the definition of class. Bases are stored in Typez object and furthermore
        'object' is added to bases.
        Every node inside node.body is recursively executed. 
        '''
        class_scope = Scope(parent = scope)
        scope[node.name] = Typez(kind='classdef', node = node, scope = class_scope)
        #docstrings
        if isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Str):
            scope[node.name].docstring = node.body[0].value.s
        for _node in node.body:
            self.eval_code(_node, class_scope)
        bases = [self.eval_code(base, scope) for base in node.bases]
        obj = self.extern_scope['object']
        bases.append(obj)
        class_scope['__bases__'] = bases
       
    @logentry
    def exec_Num(self, node, scope):
        '''
        This method proceeds code like : 1,55, etc.
        '''
        return Typez(kind='const', node = node, value = node.n, __class__ = self.extern_scope['num'])

    @logentry
    def exec_Str(self, node, scope):
        ''''
        This method proceeds code like : 'some_string_in_input_code'
        '''
        return Typez(kind='const', node = node, value = node.s, __class__ = self.extern_scope['str'])
    
    @logentry
    def exec_Name(self, node, scope):
        '''
        Method that proceeds all occurences of name. For instance : x=5 (x is a name)
        There are two cases: name is a constant (None, True, False) or name is a variable that
        has to be resolved.
        '''
        if node.id == 'None':
            return Typez(kind = 'const', node = node, value = 'None')
        if node.id == 'True':
            return Typez(kind = 'const', node = node, value = True, __class__ = self.extern_scope['bool'])
        if node.id == 'False':
            return Typez(kind = 'const', node = node, value = False, __class__ = self.extern_scope['bool'])
        res = scope.resolve(node.id, 'cascade')
        if res is None and isinstance(node.ctx,ast.Load):
            self.warn(node, "NameError: Name '"+ node.id + "' is not defined", node.id)
        return res

    @logentry
    def exec_List(self, node, scope):
        '''
        List in our implementation only holds info about one object - representant.
        This can be handful for numerous reasons: apending something in neverending while cycle would cause
        overflow in symbolic execution if we stored full list. Another advantage is quickness of execution.
        '''
        new_list = Typez(kind = 'obj', node = node, parent_scope = scope, __class__ = self.extern_scope['inf_list'])
        init = new_list.resolve('__init__','class')
        self._exec_fun(init, [new_list],{}, new_list.scope, node)      
        append = new_list.resolve('append', 'class')
        
        for item in node.elts: 
            if append:
                item_val = self.eval_code(item, scope)
                if item_val is None and hasattr(item, "id"):
                #    self.warn(node, "NameError: Name '"+ item.id + "' is not defined", item.id)
                    item_val = any_type
                self._exec_fun(append, [new_list, item_val], {}, scope, node=node) 
        return new_list

    @logentry
    def exec_Dict(self, node, scope):
        '''
        Dictionary in our implementation only holds info only about two objects: key and value.
        Reasons are the same like in exec_List.
        '''
        new_dict = Typez(kind = 'obj', node = node, parent_scope = scope, __class__ = self.extern_scope['inf_dict'])
        init = new_dict.resolve('__init__','class')
        self._exec_fun(init, [new_dict],{}, new_dict.scope, node)
        setItem = new_dict.resolve('__setitem__', 'class')
        #self.nondet=False
        for i,item in enumerate(node.values):
            item_val = self.eval_code(item, scope)
            if item_val is None and hasattr(item, "id"):
                #self.warn(node, "NameError: Name '"+ item.id + "' is not defined", item.id)
                item_val = any_type
            key_val = self.eval_code(node.keys[i],scope)
            if key_val is None and hasattr(node.keys[i], "id"):
                #self.warn(node, "NameError: Name '"+ node.keys[i].id + "' is not defined", node.keys[i].id)
                key_val = any_type
            args = [new_dict, key_val, item_val]
            self._exec_fun(setItem, args, {}, scope, node=node)    
        return new_dict
    


    @logentry
    def exec_Set(self, node, scope):
        '''
        Set in our implementation only holds info about one object - representant.
        This can be handful for numerous reasons: adding something in neverending while cycle would cause
        overflow in symbolic execution if we stored full set. Another advantage is quickness of execution.
        '''
        new_set = Typez(kind = 'object', node = node, parent_scope = scope, __class__ = self.extern_scope['inf_set'])
        init = new_set.resolve('__init__','class')
        self._exec_fun(init, [new_set],{}, new_set.scope, node)
        add =  new_set.resolve('add', 'class')
        for item in node.elts:
            item_val = self.eval_code(item, scope)
            if item_val is not None:
                self._exec_fun(add, [new_set, item_val], {}, scope, node=node) 
        return new_set

    
    @logentry
    def exec_Tuple(self, node, scope):
        '''
        Tuple in our implementation is of size 5. That should be enough for executing almost all operations between tuples (pairs,
        triples, adding them together).
        This can be handful for numerous reasons: adding something in neverending while cycle would cause
        overflow in symbolic execution if we stored full tuple. Another advantage is quickness of execution.
        '''
        new_tuple = Typez(kind = 'object', node = node, parent_scope = scope, __class__ = self.extern_scope['inf_tuple'])
        init = new_tuple.resolve('__init__','class')
        self._exec_fun(init, [new_tuple],{}, new_tuple.scope, node)
        set_item =  new_tuple.resolve('inf__setitem__', 'class')
        i=0
        for item in node.elts:
            item_val = self.eval_code(item, scope)
            if item_val is None:
                item_val = any_type
            else:
                #check whether item_val is a PlaceHolder by adding two tuples together
                if not item_val.resolve_class(self.extern_scope['PlaceHolder']):
                    index = Typez(kind='const', value = i, __class__ = self.extern_scope['num'])
                    self._exec_fun(set_item, [new_tuple, index, item_val], {}, scope, node=node) 
                    i+=1        
        return new_tuple
    
    @logentry
    def exec_Index(self,node,scope):
        '''
        This method proceeds all the indexing in our implementation. 
        '''
        return self.eval_code(node.value, scope)
    
    @logentry
    def exec_Slice(self,node,scope):
        '''
        This method proceeds all the slicing in our implementation.
        The mock object inf_slice is created.
        '''
        new_slice = Typez(kind = 'object', node = node, parent_scope = scope, __class__ = self.extern_scope['inf_slice'])
        init = new_slice.resolve('__init__','class')
        args=[new_slice]
        if node.upper is not None:
            args.append(self.eval_code(node.upper, scope))
        if node.lower is not None:
            args.append(self.eval_code(node.lower, scope))
        if node.step is not None:
            args.append(self.eval_code(node.step, scope))
        self._exec_fun(init, args,{}, new_slice.scope, node)
        return new_slice
    
    @logentry
    def exec_Subscript(self, node, scope):
        '''
        This method proceeds statements like: x[8] or x[2:6].
        We have to control whether the given structure is iterable/support indexing.
        '''
        structure = self.eval_code(node.value, scope)
        key = self.eval_code(node.slice, scope)
        get_item = structure.resolve('__getitem__','class')
        if get_item:
            return self._exec_fun(get_item, [structure, key], {}, scope, node=node)
        else:
            if hasattr(node.value, 'id'):
                self.warn(node, "object %s doesnt support indexing"%(node.value.id), node.value.id) 
            else:
                symbol = structure.scope['__class__'].node.name
                self.warn(node, "object %s doesnt support indexing"%(symbol), symbol)         
                      
    @logentry
    def exec_Expr(self, node, scope):
        '''
        This method executes the value (ast.Assign,...) of expression
        '''
        return self.eval_code(node.value, scope)


    def _exec_fun(self, fun_type, args, keywords, scope, create_scope = True, node = None):
        """
        executes function with given args in the given scope. When create_scope is True, it creates new scope for the function
        executing with parameter scope as its parent. Otherwise, it executes function in the given
        scope.
        
        """
        #if we dont know the fun_type, return any_type
        if fun_type.kind=='any':
            return any_type

        from random import randint
        
        if fun_type == self.extern_scope['inf_hasattr']:
            a=args[0]
            b=args[1]
            if b.value is not None:
                res = a.resolve(b.value)
                if res is None:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
            self.nondet=True
            bit = randint(0,1)
            if bit:
                return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
            else:
                return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
            
        
        if fun_type == self.extern_scope['inf_random']:
            self.nondet=True
            bit = randint(0,1)
            if bit:
                return Typez(kind='const', value = 1, __class__ = self.extern_scope['num'])
            else:
                return Typez(kind='const', value = 0, __class__ = self.extern_scope['num'])
        
        if fun_type == self.extern_scope['inf_equal']:
            a=args[0]
            b=args[1]
            if a.value is not None and b.value is not None:
                left = a.value
                right = b.value
                if isinstance(a.value, bool):
                    if a.value:
                        left = 1
                    else:
                        left = 0      
                if isinstance(b.value, bool):
                    if b.value:
                        right = 1
                    else:
                        right = 0
                if left==right:
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
            else:
                self.nondet=True
                bit = randint(0,1)
                if bit:
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
        
        if fun_type == self.extern_scope['inf_is']:
            #we truly determine only if the statement is in form - smth is None
            if is_none(args[1]): 
                if is_none(args[0]):
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
            else:
                self.nondet=True
                bit = randint(0,1)
                if bit:
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
        if fun_type == self.extern_scope['isinstance']:
            if isinstance(args[0],Typez) and isinstance(args[1],Typez):
                instance = args[0]
                clazz = args[1]
                
                res = instance.resolve_class(clazz)
                if not res is None:
                    return Typez(kind='const', value = True, __class__ = self.extern_scope['bool'])
                else:
                    return Typez(kind='const', value = False, __class__ = self.extern_scope['bool'])
            else:
                self.warn(node, symbol = 'isinstance error', message = 'isinstance bad arguments')

        if fun_type == self.extern_scope['inf_setattr']:
            attr = args[1]
            if isinstance(attr, Typez) and isinstance(attr.value, str):
                attr = attr.value
            if isinstance(attr, str):
                args[0].scope[attr] = args[2]
               
        if create_scope:
            fun_scope = Scope(parent = scope)
        else:
            fun_scope = scope
        def_args = fun_type.node.args.args
        def_default_args = fun_type.node.args.defaults
        def_args_names = [arg.arg for arg in def_args]
        count_given_args = len(args)+len(keywords)
        if count_given_args > len(def_args) or count_given_args+len(def_default_args)< len(def_args):
            symbol = not_none(safe_resolve(node, 'func.attr'), safe_resolve(node, 'func.id'))
            self.warn(node, symbol = symbol, message = 'bad number of arguments (%d given, %d expected)'%(len(args), len(def_args)))
        for keyword in keywords:
            if not keyword in def_args_names:
                symbol = not_none(safe_resolve(node, 'func.attr'), safe_resolve(node, 'func.id'))
                self.warn(node, symbol = symbol, message = 'unexpected keyword argument %s'%(keyword))
        
        for i,arg in enumerate(def_args):
            if i<len(args):
                if arg.arg in keywords:
                    symbol = not_none(safe_resolve(node, 'func.attr'), safe_resolve(node, 'func.id'))
                    self.warn(node, symbol = symbol, message = 'multiple arguments for keyword argument %s'%(arg.arg))
                fun_scope[arg.arg] = args[i]
            else:
                found=False
                for j,key in enumerate(keywords):
                    if key==arg.arg:
                        found=True
                        fun_scope[arg.arg]=keywords[key]
                if not found:
                    lengthFromEnd = len(def_args)-i
                    if len(def_default_args) >= lengthFromEnd:
                        fun_scope[arg.arg]=self.eval_code(def_default_args[-lengthFromEnd],scope)
                    else:
                        fun_scope[arg.arg] = any_type
        try:
            for _node in fun_type.node.body:
                self.eval_code(_node, fun_scope)
        except ReturnException as e:
            res=e.res
            if isinstance(res, Typez) and  "__class__" in res.scope and (res.scope["__class__"] == self.extern_scope['ProblemException']):    
                error = res.scope["error"]
                message = res.scope["message"]
                #symbol = res.scope["symbol"]
                symbol = None
                for key,val in scope.items():
                    if val==error:
                        symbol = key
                #when error is caused by constant, symbol is its type
                if symbol is None:
                    if hasattr(error.scope['__class__'].node, 'name'):
                        symbol = error.scope['__class__'].node.name
                    else:
                        #default symbol
                        symbol = 'Type error'
                if is_none(message):
                    #default message because it is very often used
                    message_value = "unsupported operand type"
                else:
                    message_value = message.value
                self.warn(node, message_value, symbol)
                return any_type
            
            if isinstance(res, Typez) and  "__class__" in res.scope and (res.scope["__class__"] == self.extern_scope['TypeContainer']):      
                gen_type=res.scope["T"]
                result = Typez(kind='const',__class__ = gen_type)
                if gen_type==self.extern_scope['num']:
                    print('TU: '+str(node.lineno))
                return result
                
            return res
        
        if fun_type.kind == 'classdef':
            return args[0]

    def exec_If(self, node, scope):
        '''
        In our implementation, we try to evaluate the if condition. If the value is known, then we execute the appropriate branch.
        Otherwise, we choose randomly a branch.
        '''
        from random import randint

        test_typez = self.eval_code(node.test,scope)
        if isinstance(test_typez,Typez):
            if test_typez.value is not None:
                if (not is_none(test_typez)) and test_typez.value!="" and test_typez.value!=0 and not (test_typez.scope['__class__']==self.extern_scope['bool'] and not test_typez.value):
                    for _node in node.body:
                        self.eval_code(_node, scope)
                else:
                    for _node in node.orelse:
                        self.eval_code(_node, scope)
            else:
                self.nondet=True
                bit = randint(0,1)
                if bit:
                    for _node in node.body:
                        self.eval_code(_node, scope)
                else:
                    for _node in node.orelse:
                        self.eval_code(_node, scope)
        else:
            self.warn(node, symbol = 'evaluation of condition failed', message = 'could not evaluate if condition')

    def exec_Call(self, node, scope):
        '''
        This method is resposible for exectuing calls. For instance : fun(),a.b.c.fun() or A() as a constructor. 
        '''
        #first let's find out which function should be called. This should be easy when doing func()
        #call, but it can be tricky when using constructs such as 'a.b.c.func()'

        #covers func() case
        if isinstance(node.func, ast.Name):
            logger.debug("? exec_Call "+node.func.id +" "+str(node))
            call_type = scope.resolve(node.func.id,'cascade')
            if call_type is None:
                call_type = any_type
        #covers a.b.c.func() case
        elif isinstance(node.func, ast.Attribute):
            logger.debug("? exec_Call "+node.func.attr +" "+str(node))
            call_type = self.eval_code(node.func, scope)
            if call_type == any_type:
                return any_type

        else:
            raise Exception('should not get here')

        #now we know what to invoke. Now we must distinguish whether it is func/method call or 'new'
        #statement.
        #Call-ing function or method
        if call_type.kind == 'funcdef':
            args = [self.eval_code(arg, scope) for arg in node.args]
            keywords = {}
            for keyword in node.keywords:
                keywords[keyword.arg]=self.eval_code(keyword.value, scope)
            #print("ARGS:"+str(node.func)+str(args))
            counter = 0
            for arg_eval in args:
                if arg_eval is None and hasattr(node.args[counter], 'id'):
                    self.warn(node, "NameError: Name '"+ node.args[counter].id + "' is not defined", node.args[counter].id)
                counter = counter + 1
            if call_type.is_method:
                args = [call_type.self_obj]+args
            return self._exec_fun(call_type, args, keywords, call_type.scope, node=node)

        #Call-ing as a 'new' statement
        if call_type.kind == 'classdef':
            args = [self.eval_code(arg,scope) for arg in node.args]
            keywords = {}
            for keyword in node.keywords:
                keywords[keyword.arg]=self.eval_code(keyword.value, scope)
            new = Typez(kind = 'obj', parent_scope = scope)
            args = [new]+args
            new.scope['__class__'] = call_type
            constructor = call_type.resolve('__init__', 'class')
            if constructor:
                new.obj = self._exec_fun(constructor, args, keywords, new.scope, node=node)
            return new
        if hasattr(node.func, 'id'):
            self.warn(node, message = 'nonexistent_function', symbol = node.func.id)
            return any_type
    
    @logentry
    def exec_TryFinally(self, node, scope):
        '''
        Represents block try-finally. For this purposes was implemented Exception RaiseException.
        '''
        try:
            for _node in node.body:
                self.eval_code(_node, scope)
        except RaiseException as e:
            for _node in node.finalbody:
                self.eval_code(_node, scope)
            raise e
        else:
            for _node in node.finalbody:
                self.eval_code(_node, scope)
    
    @logentry
    def exec_TryExcept(self, node, scope):
        '''
        Represents block try-except. Usually this block is nested in the block try-finally.
        For this purposes was implemented Exception RaiseException.
        '''
        try:
            for _node in node.body:
                self.eval_code(_node, scope)
            for _node in node.orelse:
                self.eval_code(_node, scope)
        except RaiseException as e:
            #najst spravnu except vetvu
            handled = False
            for _handler in node.handlers:
                _handler_type = self.eval_code(_handler.type, scope)
                if e.res.scope['__class__'] == _handler_type:
                    handled = True
                    print("nasiel som handler pre exception")
                    for _node in _handler.body:
                        self.eval_code(_node, scope)
                    break
                
            if not handled:
                raise e
    

    
    @logentry
    def exec_Module(self, node, scope):
        '''
        This method executes in node in the body of ast.Module. This kind of node
        encapsulates the whole code. Therefore, we need to resolve each part of it.
        '''
        for _node in node.body:
            self.eval_code(_node, scope)

    @logentry
    def exec_Return(self, node, scope):
        '''
        When a return statement occurs, in our implementation, exception ReturnException is thown with argument of result.
        In _exec_fun, this exception is catched.
        '''
        res = self.eval_code(node.value, scope)
        raise ReturnException(res)
    
    @logentry 
    def exec_Raise(self, node, scope):
        '''
        Similar idea like in exec_Return, just the exception is RaiseException and it is catched in exec_TryExcept.
        '''
        res = self.eval_code(node.exc,scope)
        test = res.resolve_class(self.extern_scope['Exception'])
        if test is None:
            self.warn(node, "exceptions must derive from Exception", "raise")
        else:
            raise RaiseException(res,node)
    @logentry
    def exec_Pass(self, node, scope):
        '''
        This method executes the keyword pass
        '''
        pass
    
    @logentry
    def exec_Break(self,node, scope):
        '''
        This method executes the keyword break. It is implemented as throwing BreakException that is catched in For/while cycle
        '''
        raise BreakException()
    
    @logentry
    def exec_Continue(self, node, scope):
        '''
        This method executes the keyword break. It is implemented also as throwing BreakException that is catched in For/while cycle
        '''
        raise BreakException()
     
    @logentry
    def exec_Attribute(self, node, scope):
        '''
        This method executes all atributes in the code (a.b.x.y)
        '''
        #if not isinstance(node.ctx, ast.Load):
        #    raise Exception('''Attribute should allways be executed in Load context, in the case of x.y = z the whole assignment should be handled by exec_Assign''')
        _type = self.eval_code(node.value, scope)
        if _type is None:
            if hasattr(node.value, "id"):
                #self.warn(node, "NameError: Name '"+ node.value.id + "' is not defined", node.value.id)
                pass
            #else:
                #self.warn(node, "Unidentified name value in this line is not defined", "Attribute")
            return none_type
        
        #we first try 'straight' resolution of the attribute
        res = _type.resolve(node.attr, 'straight')
        if res:
            #res.is_method = False
            #res.self_obj = None
            #print('straight resolution', node.attr)
            return res
        else:
            res = _type.resolve(node.attr, 'class')
            if res is not None:
                # we are creating partial
                res = res.clone()
                res.is_method = True
                res.self_obj = _type
                #print('class resolution', node.attr, res, id(res), res.is_method)
                return res
            else:
                self.warn(node, message = "nonexistent_attribute", symbol = node.attr)
                return any_type
    
    @logentry
    def exec_ListComp(self, node, scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_DictComp(self, node, scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_SetComp(self, node, scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_GeneratorExp(self, node, scope):
        '''
        TODO
        '''
        pass

    @logentry
    def exec_comprehension(self, node, scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_Import(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_ImportFrom(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_alias(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_With(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_Yield(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_YieldFrom(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_Global(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_NonLocal(self,node,scope):
        '''
        TODO
        '''
        pass
    
    @logentry
    def exec_Starred(self,node,scope):
        '''
        TODO
        '''
        pass
            
    @logentry
    def exec_Lambda(self, node, scope):
        '''
        TODO
        '''
        pass

    def eval_code(self, node, scope):
        """
main method of the parser, it executes code under certain node within the given scope (if
the scope is not given, we use typez.extern_scope as a highest scope possible). It returns
return value of the code.

the whole idea is to dispatch work to exec_<ast_node_name> functions; exec_name functions
are doing only minimum ammount of job to correctly cover the execution of the specific piece of
code, recursively using eval_code to evaluate values of their children nodes.
"""     
        if self.breakpoint and hasattr(node, 'lineno') and node.lineno == self.breakpoint:
            print("breakpoint occured!!!")
            raise SuperBreakException()

        self.visited_ast_nodes.append(node)
        name = 'exec_'+node.__class__.__name__
        handler = Parser.__dict__[name]
        return handler(self, node, scope)

    def eval_in_root(self, node, breakpoint=None):
        try:
            self.breakpoint=breakpoint
            return self.eval_code(node, self.root_scope)
        except RaiseException as e:
            self.warn(e.statement, 'unhandled raise of exception', 'Exception')
        except SuperBreakException as e:
            print("breakpoint occured, eval terminated!!!")
            
"""
class that encaptulates running parser x times and returns set of problems and warnings

has set of problems, warnings and a parser. Parser is being run numberOfIteration times and
we gather information about problems as a result of each iteration.
"""
class FinalParser:
    
    def __init__(self,num_iter=20):
        self.number_of_iterations = num_iter
        self.problems = []
        self.visited_nodes = []
        self.warnings = []
        self.removed = []
        self.nondet=False
        self.scopes=[]
        self.extern_scope = None
        
    def eval_in_root(self, node, breakpoint=None):
        def diff(a, b):
            return [aa for aa in a if aa not in b]

        for i in range(0, self.number_of_iterations):
            #print("--------number of iteration %d--------"%(i))
            if self.extern_scope is None:
                p = Parser()
                self.extern_scope = p.extern_scope
            else:
                p = Parser(self.extern_scope)
            p.eval_in_root(node,breakpoint)
            self.scopes.append(p.root_scope)
            #budeme vediet ci sa stalo nieco nedeterministicke
            if hasattr(p, 'nondet') and p.nondet:
                self.nondet=True
            
            for new_problem in p.problems:
                if not new_problem in self.problems:
                    if not new_problem.node in self.visited_nodes:
                        self.problems.append(new_problem)
                    else:
                        if not new_problem in self.warnings:
                            self.warnings.append(new_problem)
            
            for old_problem in diff(self.problems,p.problems):
                if old_problem.node in p.visited_ast_nodes and not old_problem in p.problems:
                    self.problems.remove(old_problem)
                    if not old_problem in self.warnings:
                        self.warnings.append(old_problem)
                                    
            for _node in p.visited_ast_nodes:                
                if not _node in self.visited_nodes:
                    self.visited_nodes.append(_node)
                        
    
    def resolve(self,symbol):
        res=[]
        for scope in self.scopes:
            res.append(scope.resolve(symbol))
        return res
        
    def get_all_possible_attr(self,symbol):
        types=self.resolve(symbol)
        atrs=[]
        for t in types:
            if t:
                res=t.get_atrs()
                for e in res:
                    if not e in atrs:
                        atrs.append(e)
        return sorted(atrs)
        

if __name__ == '__main__':
    p = Parser()
