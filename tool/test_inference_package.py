import unittest
import ast
import logging
import inf.parsing.utils as utils
from inf.inference.parse_ast import Parser
from inf.inference.parse_ast import FinalParser
from  inf.inference.typez import (
        Scope,
        Typez,
        any_type,
        none_type
        )
import re


def makecode(code):
    return re.sub(r'[ \t]+\|','',code)

class InferTestCase(unittest.TestCase):

    def assert_no_problem(self):
        self.assertEqual(len(self.parser.problems), 0)

    def assertIsNum(self, typez):
        self.assertEqual(typez.scope['__class__'], self.num_class)

    def assertIsStr(self, typez):
        self.assertEqual(typez.scope['__class__'], self.str_class)
        
    def assertIsBool(self, typez):
        self.assertEqual(typez.scope['__class__'], self.bool_class)

class TestResolve(InferTestCase): #{{{

    def setUp(self):
        num_class = Typez(kind = 'classdef')
        num_class.scope['__add__'] = Typez(kind = 'funcdef')

        pr_num = Typez(kind = 'pr_num', __class__ = num_class )
        pr_str = Typez(kind = 'pr_str')
        self.scope = Scope(is_root = True)
        self.scope.update({'xxx':pr_str})

        scope1 = Scope(parent = self.scope)
        scope1.update({'a': pr_num, 'b': pr_str})
        self.type1 = Typez(kind = 'obj', scope = scope1)

        scope2 = Scope(parent = self.scope)
        scope2.update({'c': pr_num, 'd': pr_str})
        self.type2 = Typez(kind = 'obj', scope = scope2)
        self.type2 = scope2

        scope12 = Scope(parent = self.scope)
        scope12.update({'a':self.type1, 'b': self.type2})
        self.type12 = Typez(kind = 'obj', scope = scope12)

        self.scope.update({'type1':self.type1, 'type2': self.type2, 'type12': self.type12})

    def test_resolve_type1_in_scope(self):
        res = self.scope.resolve('type1', 'straight')
        self.assertEqual(res, self.type1)

    def test_resolve_in_type(self):
        res = self.type1.resolve('a', 'straight')
        self.assertEqual(res.kind,'pr_num')
        self.assertEqual(self.scope.resolve('c'), None)


    def test_resolve_cascade(self):
        self.assertRaises(Exception, self.type1.resolve, 'xxx','cascade')
        res1 = self.type1.scope.resolve('xxx','cascade')
        res2 = self.scope.resolve('xxx','straight')
        self.assertEqual(res1,res2)

    def test_resolve_class(self):

        num = self.type1.resolve('a', 'straight')
        self.assertRaises(Exception, num.resolve, '__add__', 'cascade')
        add = num.resolve('__add__', 'straight')
        self.assertEqual(add, None)
        add = num.resolve('__add__', 'class')
        self.assertIsInstance(add, Typez)
        self.assertEqual(add.kind, 'funcdef')

#}}}

class TestScope(InferTestCase): #{{{
    def setUp(self):
        scope = Scope(is_root = True)
        scope['a'] = 'a'
        scope['b'] = 'b'
        child_scope = Scope(parent = scope)
        child_scope['c'] = 'c'
        self.scope = scope
        self.child_scope = child_scope

    def test_basic(self):
        self.assertEqual(self.scope.resolve('a', 'straight'), 'a')
        self.assertEqual(self.scope['a'], 'a')
        self.assertEqual(self.scope.resolve('a', 'cascade'), 'a')
        self.assertEqual(self.scope.resolve('c', 'cascade'), None)
        self.assertEqual(self.child_scope.resolve('a', 'straight'), None)
        self.assertEqual(self.child_scope.resolve('a', 'cascade'), 'a')
        self.assertEqual(self.child_scope.resolve('c', 'straight'), 'c')
        self.assertEqual(self.child_scope.resolve('c', 'cascade'), 'c')
        self.assertRaises(Exception, self.child_scope.resolve, 'c', 'class')

#}}}

class TestInfer(InferTestCase): #{{{

    def setUp(self):
        self.parser = Parser()
        self.finalParser = FinalParser()
        self.num_class = self.parser.extern_scope['num']
        self.str_class = self.parser.extern_scope['str']
        self.bool_class = self.parser.extern_scope['bool']
        

    def test_simple_parse(self):
        code = makecode("""
        |x = 3
        |a = 'ahoj'
        |y = 6
        |z = 3 + x
        |zz = x + y
        |b = 'jozo'
        |c = a + b
        |x = 'mumly'
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        x = module_scope.resolve('x')
        y = module_scope.resolve('y')
        z = module_scope.resolve('z')
        zz = module_scope.resolve('zz')
        a = module_scope.resolve('a')
        b = module_scope.resolve('b')
        c = module_scope.resolve('c')
        self.assertIsStr(x)
        self.assertIsNum(y)
        self.assertIsNum(z)
        self.assertIsNum(zz)
        self.assertIsStr(a)
        self.assertIsStr(b)
        self.assertIsStr(c)

    def test_fun_parse(self):
        code = makecode("""
        |def mean(x,y):
        |    return (x+y)/2
        
        |def gean(x,y):
        |    return x+y
        
        |x = 3
        |y = x+2
        |z = mean(x,y)
        |x = "jozo"
        |zz = gean(x,"fero")
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        x = module_scope.resolve('x')
        y = module_scope.resolve('y')
        z = module_scope.resolve('z')
        zz = module_scope.resolve('zz')
        self.assertIsStr(x)
        self.assertIsNum(y)
        self.assertIsNum(z)
        self.assertIsStr(zz)
    
    def test_default_object(self):
        code = makecode("""
        |class A():
        |    pass
        |a = A()
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a = module_scope.resolve('a')
        __setattr__ = a.resolve('__setattr__', 'straight')
        self.assertEqual(__setattr__, None)
        __setattr__ = a.resolve('__setattr__', mode = 'class')
        self.assertEqual(__setattr__.node.name, '__setattr__')

    def test_closure(self):
        code = makecode("""
        |def f(x):
        |    z = x
        |    def g(y):
        |        return(x+y)
        |    return g
        
        |g1 = f(3)
        |g2 = f('jozo')
        
        |a = g1(4)
        |b = g2('fero')
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a = module_scope.resolve('a')
        b = module_scope.resolve('b')
        self.assertIsNum(a)
        self.assertIsStr(b)


    def test_class(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y, z):
        |        self.x = x
        |        self.y = y
        |        w = 'johnie'
        |
        |a = A(3,"ahoj", "svet")
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a = module_scope.resolve('a')
        self.assert_no_problem();
        self.assertIsNum(a.scope['x'])
        self.assertIsStr(a.scope['y'])
        self.assertNotIn('w', a.scope)
        self.assertNotIn('z', a.scope)
        self.assertEqual(a.scope.resolve('z'),None)

    def test_override_setattr(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y):
        |        pass
        |
        |    def __setattr__(self, attr, val):
        |        object.__setattr__(self, attr, 4)
        |
        |
        |a = A(3,4)
        |a.x = 'jozo'
        |key = 'z'
        |object.__setattr__(a,key,'jozo')
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a = module_scope.resolve('a')
        self.assert_no_problem();
        self.assertIsNum(a.scope['x'])
        self.assertIsStr(a.scope['z'])

    def test_method_lookup(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x):
        |        self.x = x
        
        |    def get_x(self):
        |        return self.x
        
        |a = A('jozo')
        |b = a.get_x()
        |a = A(3)
        |c = a.get_x()
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        self.assert_no_problem();
        a = module_scope.resolve('a')
        A = module_scope.resolve('A')
        self.assertNotIn('get_x', a.scope)
        self.assertIn('get_x', A.scope)
        b = module_scope.resolve('b')
        c = module_scope.resolve('c')
        self.assertIsStr(b)
        self.assertIsNum(c)

    def test_method_manipulation(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y):
        |        self.x = x
        |        self.y = y
        |
        |    def fun1(self):
        |        return self.x+self.y
        |
        |
        |a = A(3,4)
        |a.fun1()
        |fun2 = a.fun1
        |a.fun3 = a.fun1
        |z2 = fun2()
        |z3 = a.fun3()
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        z2 = module_scope.resolve('z2')
        self.assertIsNum(z2)
        z3 = module_scope.resolve('z3')
        self.assertIsNum(z3)

    def test_class_closure(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x):
        |        self.x = x
        
        |    def get_x(self):
        |        return self.x
        
        |a = A('jozo')
        |getx = a.get_x
        |getx_class1 = A.get_x
        |getx_class2 = A.get_x
        |x1 = getx()
        |x2 = getx_class1()
        |x3 = getx_class2(a)
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        self.assertEqual(1, len(self.parser.problems))
        self.assertEqual('getx_class1', self.parser.problems[0].symbol)
        x1 = module_scope.resolve('x1')
        x3 = module_scope.resolve('x3')
        self.assertIsStr(x1)
        self.assertIsStr(x3)

    def test_inheritance(self):
        code = makecode("""
        |class A:
        |    def __init__(self):
        |        pass
        |
        |    def get_x(self):
        |        return self.x
        
        |class B(A):
        |    def __init__(self):
        |        pass
        |
        |    def get_y(self):
        |        return self.y
        
        |b = B()
        |b.x = 'jozo'
        |b.y = 4
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        self.assertEqual(len(self.parser.problems), 0)
        b = module_scope.resolve('b')
        print(b)
        self.assertIsNum(b.scope['y'])
        self.assertIsStr(b.scope['x'])
        self.assertEqual(b.resolve('get_x', 'class').kind, 'funcdef')
    
    def test_function_return(self):
        code = makecode("""
        |def g():
        |    return "ahoj"
        |
        |
        |def f():
        |    x=1
        |    y=2
        |    g()
        |    return x+y;
        |
        |z = f()
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        self.assertEqual(len(self.parser.problems), 0)
        z = module_scope.resolve('z')
        self.assertIsNum(z)
        
    def test_finalParser(self):
        code = makecode("""
        |class A:
        |    x = 5+1
        |
        |a = A()
        |
        |b = a.something
        |
        |if a.x:
        |    a.y=1
        |else:
        |    a.z=1
        |
        |if a.x:
        |    a.y
        |else:
        |    a. z
""")     
        node = ast.parse(code, mode = 'exec')
        #self.parser.eval_in_root(node)
        self.finalParser.eval_in_root(node)
        #module_scope = self.parser.root_scope
        #module_scope = self.finalParser.parser.root_scope
        self.assertTrue(self.finalParser.nondet)
        self.assertEqual(len(self.finalParser.problems), 1)
        self.assertEqual(len(self.finalParser.warnings), 2)
        problem_symbols = {problem.symbol for problem in self.finalParser.problems}
        self.assertEqual(problem_symbols, {'something'})
        warning_symbols = {problem.symbol for problem in self.finalParser.warnings}
        self.assertEqual(warning_symbols, {'y','z'})
        
        
    
    def test_correct_inheritance(self):
        code = makecode("""
        |class A:
        |    x = 5
        |
        |class B:
        |    x = 'test'
        |
        |class C(A,B):
        |    pass
        |
        |class D(B,A):
        |    pass
        |
        |class E(A):
        |    pass
        |
        |class F(E,B):
        |    pass
        |
        |a = C()
        |b = D()
        |c = F()
""")

        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a = module_scope.resolve('a')
        b = module_scope.resolve('b')
        c = module_scope.resolve('c')
        self.assertIsNum(a.resolve('x', 'class'))
        self.assertIsStr(b.resolve('x', 'class'))
        self.assertIsNum(c.resolve('x', 'class'))

    def test_isinstance_simple(self):
        code = makecode("""
        |class A:
        |    x = 4
        |
        |class B(A):
        |    y = 3
        |
        |class C:
        |    x = 2
        |
        |b = B()
        |a = A()
        |
        |c = isinstance(b,A)
        |d = isinstance(b,C)
        |
        |b.y
        |b.x
        |b.z
    """)
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        
        a = module_scope.resolve('a')
        print("a value: "+ str(a))
        c = module_scope.resolve('c')
        print("c value: "+ str(c))
        d = module_scope.resolve('d')
        print("d value: "+ str(d))
        
        #problem_symbols = {problem.symbol for problem in self.parser.problems}
        #print("PROBLEM: "+str(problem_symbols))
        
    def test_isinstance_expert(self):
        code = makecode("""
        |class A:
        |    x = 4
        |
        |class B(A):
        |    y = 3
        |
        |def returnInstanceOfA():
        |    a = A()
        |    return a
        |
        |def returnA():
        |    return A
        |
        |def returnB():
        |    return B
        |
        |a = A()
        |b = B()
        |
        |c = isinstance(returnInstanceOfA(),returnA())
        |d = isinstance(b,returnB())
        |e = isinstance(b,returnA())
    """)
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        
        c = module_scope.resolve('c')
        d = module_scope.resolve('d')
        e = module_scope.resolve('e')
        self.assertTrue(c.value)
        self.assertTrue(d.value)
        self.assertTrue(e.value)
        
        #problem_symbols = {problem.symbol for problem in self.parser.problems}
        #print("PROBLEM: "+str(problem_symbols))
        
    def test_bin_ops(self):
        code = makecode("""
        |x = 3
        |y = 5
        |zz = y-x
        |a = True
        |b=5<6
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        zz = module_scope.resolve('zz')
        a = module_scope.resolve('a')
        print("zz: " + str(zz.value))
        self.assertIsNum(zz)
        self.assertTrue(a)
        self.assertIsBool(a)
        print("a: " + str(a))
        b = module_scope.resolve('b')
        self.assertIsBool(b)
        #self.assertIsNum(a)
        
    def test_if(self):
        code = makecode("""
        |c=True
        |if c:
        |    c1=1
        |v="True"
        |if v:
        |    v1=1
        |n="False"
        |if n:
        |    n1=1
        |m=False
        |m1="test"
        |if m:
        |    m1=1
        |a=None
        |a1="test"
        |if a:
        |    a1=1
        |s="None"
        |if s:
        |    s1=1
        |d=0
        |d1="test"
        |if d:
        |    d1=1
        |f=1
        |if f:
        |    f1=1
        |h=""
        |h1="test"
        |if h:
        |    h1=1
        |j="0"
        |if j:
        |    j1=1
        |k="1"
        |if k:
        |    k1=1
        |g=-1
        |if g:
        |   g1=1
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        c1=module_scope.resolve('c1')
        self.assertIsNum(c1)
        v1=module_scope.resolve('v1')
        self.assertIsNum(v1)
        n1=module_scope.resolve('n1')
        self.assertIsNum(n1)
        m1=module_scope.resolve('m1')
        self.assertIsStr(m1)
        a1=module_scope.resolve('a1')
        self.assertIsStr(a1)
        s1=module_scope.resolve('s1')
        self.assertIsNum(s1)
        d1=module_scope.resolve('d1')
        self.assertIsStr(d1)
        f1=module_scope.resolve('f1')
        self.assertIsNum(f1)
        g1=module_scope.resolve('g1')
        self.assertIsNum(g1)
        h1=module_scope.resolve('h1')
        self.assertIsStr(h1)
        j1=module_scope.resolve('j1')
        self.assertIsNum(j1)
        k1=module_scope.resolve('k1')
        self.assertIsNum(k1)
        
    def test_externs(self):
        code = makecode("""
        |f=3.5
        |x=5
        |y=3
        |s="retazec"
        |z=x+s
        |b=s+x
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        problem_symbols = {problem.symbol for problem in self.parser.problems}
        for problem in self.parser.problems:
            print(problem)
        self.assertEqual(problem_symbols, {'s','x'})
        z=module_scope.resolve('z')
        self.assertEqual(z, any_type)
        x=module_scope.resolve('x')
        print(str(x))
        
    def test_obj_const(self):
        code = makecode("""
        |class A:
        |    x=4
        |
        |a=A()
        |a.z="string"
        |y=3
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        problem_symbols = {problem.symbol for problem in self.parser.problems}
        for problem in self.parser.problems:
            print(problem)
        #self.assertEqual(problem_symbols, {'s'})
        a=module_scope.resolve('a')
        self.assertIsStr(a.scope['z'])
        self.assertEqual('obj', a.scope['z'].kind)
        y=module_scope.resolve('y')
        self.assertIsNum(y)
        self.assertEqual('obj', y.kind)
        
    def test_multiple_targets_assign(self):
        code = makecode("""
        |class A(object):
        |    def __init__(self):
        |        x="test"
        |a=A()
        |a.x=b=c=1
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        a=module_scope.resolve('a')
        self.assertIsNum(a.scope['x'])
        b=module_scope.resolve('b')
        self.assertIsNum(b)
        c=module_scope.resolve('c')
        self.assertIsNum(c)
    
    def test_raise(self):
        code = makecode("""
        |raise 1
""")
        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        problem_symbols = {problem.symbol for problem in self.parser.problems}
        self.assertEqual(problem_symbols, {'raise'})
    
    def test_finally(self):
        code = makecode("""
        |class MyError(Exception):
        |    pass
        |
        |def doBadStuff():
        |    raise MyError()
        |
        |try:
        |    y="test"
        |    doBadStuff()
        |    y=1
        |finally:
        |    z=1
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        y=module_scope.resolve('y')
        self.assertIsStr(y)
        z=module_scope.resolve('z')
        self.assertIsNum(z)
        self.assertEqual(len(self.parser.problems),1)
        print(self.parser.problems)
    
    def test_except(self):
        code = makecode("""
        |class MyError(Exception):
        |    pass
        |
        |def doBadStuff():
        |    raise MyError()
        |
        |z=1
        |x="smth"
        |t="fasfas"
        |try:
        |    y="test"
        |    doBadStuff()
        |    y=1
        |except MyError:
        |    x=1
        |else:
        |    t=False
        |z="something"
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        y=module_scope.resolve('y')
        self.assertIsStr(y)
        x=module_scope.resolve('x')
        self.assertIsNum(x)
        z=module_scope.resolve('z')
        self.assertIsStr(z)
        t=module_scope.resolve('t')
        self.assertIsStr(t)
        
    def test_complex_try_statement(self):
        code = makecode("""
        |class MyError(Exception):
        |    pass
        |
        |class MyNextError(Exception):
        |    pass
        |
        |def doBadStuff():
        |    raise MyError()
        |
        |def executeRiskyStuff():
        |    try:
        |        doBadStuff()
        |    except MyNextError:
        |        pass
        |    finally:
        |        pass
        |
        |z=1
        |x="smth"
        |t="fasfas"
        |try:
        |    y="test"
        |    executeRiskyStuff()
        |    y=1
        |except MyError:
        |    x=1
        |else:
        |    t=False
        |z="something"
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        y=module_scope.resolve('y')
        self.assertIsStr(y)
        x=module_scope.resolve('x')
        self.assertIsNum(x)
        z=module_scope.resolve('z')
        self.assertIsStr(z)
        t=module_scope.resolve('t')
        self.assertIsStr(t)
        
    def test_list(self):
        code = makecode("""
        |class A:
        |    x=4
        |    def test_funkcia(self):
        |        print("nieco")
        |
        |a = A()
        |l = [a,'test']
        |l[0].test_funkcia()
        |b = ['jozo',l]
        |b[1][0].test_funkcia()
        |test = t
        |b[0]=1
""")
        
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        self.assertTrue(self.finalParser.nondet)
        self.assertEqual(len(self.finalParser.problems), 1)
        self.assertEqual(len(self.finalParser.warnings), 2)
        warning_symbols = {problem.symbol for problem in self.finalParser.warnings}
        self.assertEqual(warning_symbols, {'test_funkcia'})
    
    def test_set(self):
        code = makecode("""
        |set1 = {1,2,3}
        |set2 = {5,6,7}
        |
        |
""")
        
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        #self.assertEqual(len(self.finalParser.problems), 2)
        
    def test_for_and_while(self):
        code = makecode("""
        |class A:
        |    x=4
        |    def test_funkcia(self):
        |        print("nieco")
        |
        |a = 'jozo'
        |a = t
        |
        |for x in range(l,5):
        |    c = x
        |    a.test_funkcia()
        |
        |cc = x
        |
        |count = 0
        |while count < 10:
        |    print('hocico')
        |    print(count)
        |    b.test_funkcia()
        |
""")
        
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        #self.assertEqual(len(self.parser.problems), 2)
        for problem in self.parser.problems:
            print(str(problem))
        module_scope = self.parser.root_scope
        c = module_scope.resolve('c')
        print("C: "+str(c))
        
    def test_optional_args(self):    
        code = makecode("""
        |class A:
        |    x=4
        |
        |def optionalArgs(a,b=1,c=True):
        |    print(a.x)
        |    return b
        |
        |o=A()
        |x=optionalArgs(o)
        |y=optionalArgs(o,'test')
        |z=optionalArgs(o,3,5)
        |u=optionalArgs(o,3,5,9)
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        x = module_scope.resolve('x')
        self.assertIsNum(x)
        y = module_scope.resolve('y')
        self.assertIsStr(y) 
        for problem in self.parser.problems:
            print(str(problem))
        self.assertEqual(len(self.parser.problems), 1)
    
    def test_keyword_args(self):
        code = makecode("""
        |class A:
        |    x=4
        |
        |def func(a,b,c):
        |    print(a.x)
        |    print(b.x)
        |    print(c)
        |
        |z=A()
        |func(z,c=3,b=z)
        |func(z,c=3,a=1)
        |func(a=z,c=1,d=3)
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
    
    def test_complex_args(self):
        code = makecode("""
        |class A:
        |    def __init__(self,x,y=1,z=True):
        |        self.x=x
        |        self.y=y
        |        self.z=z
        |
        |a=A("test",z=1,y=True)
        |x=a.x
        |y=a.y
        |z=a.z
        |
        |b=A("test")
        |x1=b.x
        |y1=b.y
        |z1=b.z
        |
        |c=A("test",z=1)
        |x2=c.x
        |y2=c.y
        |z2=c.z
        |
        |d=A(z=1,b=2,y=3)
        |e=A(1,z=1,x=True)
        |f=A(1,2,3,4)
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        x = module_scope.resolve('x')
        self.assertIsStr(x)
        y = module_scope.resolve('y')
        self.assertIsBool(y)
        z = module_scope.resolve('z')
        self.assertIsNum(z)
        x1 = module_scope.resolve('x1')
        self.assertIsStr(x1)
        y1 = module_scope.resolve('y1')
        self.assertIsNum(y1)
        z1 = module_scope.resolve('z1')
        self.assertIsBool(z1)
        x2 = module_scope.resolve('x2')
        self.assertIsStr(x2)
        y2 = module_scope.resolve('y2')
        self.assertIsNum(y2)
        z2 = module_scope.resolve('z2')
        self.assertIsNum(z2)
        for problem in self.parser.problems:
            print(str(problem))
        self.assertEqual(len(self.parser.problems), 3)
            
    def test_bool_ops(self):
        code = makecode("""
        |x=8
        |y=False
        |z=True
        |u=1568
        |res=False
        |if x and y or u and z:
        |    res=True
        |else:
        |    res="test"
        |
        |if y or z:
        |    x="test"

""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        res=module_scope.resolve('res')
        self.assertIsBool(res)
        x=module_scope.resolve('x')
        self.assertIsStr(x)
    
    def test_dict(self):
        code = makecode("""
        |class A(object):
        |    def __init__(self):
        |        self.x = 5
        |a=A()
        |d={1:"test1"}
        |d[1] = a
        |print(d[1].x)
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        #self.assertTrue(self.finalParser.nondet)
        #self.assertEqual(len(self.finalParser.problems), 1)
        self.assertEqual(len(self.finalParser.warnings), 1)
        warning_symbols = {problem.symbol for problem in self.finalParser.warnings}
        self.assertEqual(warning_symbols, {'x'})
    
    def test_set_repr(self):
        code = makecode("""
        |s={1,2,3}
        |x=s.pop()
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        self.assertEqual(len(self.parser.problems), 0)
        x = module_scope.resolve('x')
        self.assertIsNum(x)
        
    def test_set_ops(self):
        code = makecode("""
        |class A(object):
        |    def __init__(self):
        |        self.x=4
        |s={1,2,3}
        |t={2,3,4}
        |z= s and t
        |z.pop()
        |a=A()
        |z.add(a)
        |b=z.pop()
        |b.x
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        #self.assertTrue(self.finalParser.nondet)
        self.assertEqual(len(self.finalParser.problems), 0)
        self.assertEqual(len(self.finalParser.warnings), 1)
        warning_symbols = {problem.symbol for problem in self.finalParser.warnings}
        self.assertEqual(warning_symbols, {'x'})
    
    def test_unary_ops(self):
        code = makecode("""
        |x=1
        |y=-x
        |z=+x
        |u=~x
        |w=not x
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        y = module_scope.resolve('y')
        self.assertIsNum(y)
        z = module_scope.resolve('z')
        self.assertIsNum(z)
        u = module_scope.resolve('u')
        self.assertIsNum(u)
        w= module_scope.resolve('w')
        self.assertIsBool(w)
        print(w)
    
    def test_num_equal(self):
        code = makecode("""
        |x=1
        |y=3
        |z="test"
        |if y==x:
        |    z=2
        |else:
        |    z=False
        |v=1
        |if x==1:
        |    v="test"
        |w=x+y
        |if w==4:
        |    w=p
        |else:
        |    w=q
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        #self.assertTrue(self.finalParser.nondet)
        self.assertEqual(len(self.finalParser.problems), 2)
        self.assertEqual(len(self.finalParser.warnings), 0)
        problem_symbols = {problem.symbol for problem in self.finalParser.problems}
        self.assertEqual(problem_symbols, {'p','q'})
        


    def test_tuple(self):
        code = makecode("""
        |t = (1,2,3,4)
        |s = ("TEST",)
        |v = [5]
        |u = t+s
        |x = u[2]
        |m = u[4]
        |y = u[0:3]
        |z = t+v
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        x = module_scope.resolve('x')
        self.assertIsNum(x)
        print("x: " + str(x))
        m = module_scope.resolve('m')
        print("m: "+ str(m))
        self.assertIsStr(m)
        #z = module_scope.resolve('z')
        #self.assertIsNum(z)
        #u = module_scope.resolve('u')
        #self.assertIsNum(u)
        #w= module_scope.resolve('w')
        #self.assertIsBool(w)
        #print(w)
    
    def test_scope_merging(self):
        code = makecode("""
        |class A:
        |    def __init__(self):
        |        self.x=4
        |
        |c=5+6
        |a=A()
        |if c:
        |    a.y=1
        |else:
        |    a.z=2
        |
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        #self.assertTrue(self.finalParser.nondet)
        self.assertEqual(len(self.finalParser.problems), 0)
        self.assertEqual(len(self.finalParser.warnings), 0)
        #module_scope=self.finalParser.finalScope
        a_atrs = self.finalParser.get_all_possible_attr('a')
        self.assertEqual(len(a_atrs),8)
        
    
    def test_break_continue(self):
        code = makecode("""
        |z="test"
        |for x in [1,2,3,4]:
        |    print(x)
        |    y=2
        |    break
        |    z=2
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        y = module_scope.resolve('y')
        self.assertIsNum(y)
        z = module_scope.resolve('z')
        self.assertIsStr(z)

    def test_inc_dec(self):
        code = makecode("""
        |class A:
        |    def __init__(self):
        |        self.x = 4
        |x=1
        |z=2
        |x+=z
        |a=A()
        |a.x+=1
""")
        node=ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        x = module_scope.resolve('x')
        print("x"+str(x))
        a = module_scope.resolve('a')
        self.assertIsNum(a.scope['x'])
        print("a.x: " + str(a.scope['x']))
        
    def test_complex_example(self):
        code = makecode("""
        |class EmptyWareHouseException:
        |    pass
        |class FullWareHouseException(Exception):
        |    pass
        |class Farm:
        |    def __init__(self,name,size):
        |        self.name = name
        |        self.sizeOfWareHouse = size
        |        self.currentSize = 0
        |    def produceOneUnit(self):
        |        if self.currentSize==self.sizeOfWareHouse:
        |           raise FullWareHouseException()    
        |        self.currentSize += 1
        |    def consumeOneUnit(self):
        |        if self.currentSize==0:
        |            raise EmptyWareHouseException()
        |        self.currentSize -= 1
        |
        |farm = Farm(size=50,name='Farm from wonderland')
        |farm.produceOneUnit()
        |farm.consumeOneUnit()
        |farm.produceOneUnit()
""")
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        print("P:" +str(self.finalParser.problems))
        print("W:" +str(self.finalParser.warnings))
        #self.assertTrue(self.finalParser.nondet)
        #self.assertEqual(len(self.finalParser.problems), 2)
        #self.assertEqual(len(self.finalParser.warnings), 0)
        #problem_symbols = {problem.symbol for problem in self.finalParser.problems}
        #self.assertEqual(problem_symbols, {'p','q'})
    
    def test_complex_example2(self):
        code = makecode('''
        |class Element(object):
        |    def __init__(self):
        |        self.data = 10
        |    def printX(self):
        |        print(self.x) #error
        |
        |instanceOfElement = Element()
        |testList = [instanceOfElement, "test"]
        |testList[0].printX()
        |10 + testList[1] #error
''')
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.finalParser.eval_in_root(node)
        print("P:" +str(self.finalParser.problems))
        print("W:" +str(self.finalParser.warnings))


    def test_tuple_assign(self):
        code = makecode('''
        |def makePair(x,y):
        |    return (x,y)
        |a,b = makePair(5,'five')
''')
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
    def test_help(self):
        code = makecode('''
        |def func():
        |    """
        |    vnjvndfkvns cnscksdcnsj
        |    """
        |    x=4
        |i[3]
        
''')
        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        module_scope = self.parser.root_scope
        for problem in self.parser.problems:
            print(str(problem))
        f = module_scope.resolve('func')
        if hasattr(f,'docstring'):
            print(f.docstring)
        #self.assertIsNum(y)
        #z = module_scope.resolve('z')
        #self.assertIsNum(z)
        #u = module_scope.resolve('u')
        #self.assertIsNum(u)
        #w= module_scope.resolve('w')
        #self.assertIsBool(w)
        #print(w)
class TestWarnings(InferTestCase): #{{{
    
    def setUp(self):
        self.parser = Parser()
        self.num_class = self.parser.extern_scope['num']
        self.str_class = self.parser.extern_scope['str']

    def test_nonexistent_attribute(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y):
        |        self.x = x
        |        self.y = y
        |
        |a = A(3,4)
        |a.x = a.z
        |a.z = a.x
        |a.y = a.z
        |a.w = a.w
        |a.t = t
        |t = a.u
""")

        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        problem_symbols = {problem.symbol for problem in self.parser.problems}
        print(problem_symbols)
        self.assertEqual(problem_symbols, {'w', 'z' , 'u', 't'})

    def test_nonexistent_function(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y):
        |        self.x = x
        |        self.y = y
        |
        |    def fun1(self):
        |        return self.x+self.y
        |
        |a = A(3,4)
        |a.z = a.fun1()
        |a.gun1()
        |a.fun2 = a.fun1
        |a.fun2()
        |# since the problem with nonexistent gun1 is already reported, gun1 and gun2 are to be considered as
        |# any_type making all invocations and other manipulations with it legal
        |a.gun2 = a.gun1
        |a.gun2()
        |a.gun3()
""")

        node = ast.parse(code, mode = 'exec')
        self.parser.eval_in_root(node)
        #problem_symbols = {problem.symbol for problem in self.parser.problems}
        #self.assertEqual(problem_symbols, {'gun1', 'gun3'})

    def test_nonexistent_class(self):
        code = makecode("""
        |class A:
        |    def __init__(self, x, y):
        |        self.x = x
        |        self.y = y
        |
        |class B:
        |    pass
        |
        |a = A(1,2)
        |b = B()
        |c = C()
        |a = D()
""")

        node = ast.parse(code, mode = 'exec')
        print(utils.astNode_to_tree(node))
        self.parser.eval_in_root(node)
        problem_symbols = {problem.symbol for problem in self.parser.problems}
        self.assertEqual(problem_symbols, {'C', 'D'})
        
    

if __name__ == '__main__':
    run_all = True
    #run_all = False

    if run_all:
        logger = logging.getLogger('')
        logger.setLevel(logging.WARN)
        unittest.main()
    else:
        suite = unittest.TestSuite()
        #suite.addTest(TestInfer("test_isinstance_simple"))
        #suite.addTest(TestInfer("test_isinstance_expert"))
        #suite.addTest(TestInfer("test_if"))
        #suite.addTest(TestInfer("test_bin_ops"))
        #suite.addTest(TestInfer("test_inheritance"))
        #suite.addTest(TestWarnings("test_nonexistent_attribute"))
        #suite.addTest(TestInfer("test_externs"))
        #suite.addTest(TestInfer("test_method_lookup"))
        #suite.addTest(TestInfer("test_obj_const"))
        #suite.addTest(TestInfer("test_help"))
        #suite.addTest(TestInfer("test_raise"))
        #suite.addTest(TestInfer("test_except"))
        #suite.addTest(TestInfer("test_finally"))
        #suite.addTest(TestInfer("test_complex_try_statement"))
        #suite.addTest(TestInfer("test_finalParser"))
        #suite.addTest(TestInfer("test_multiple_targets_assign"))
        suite.addTest(TestInfer("test_list"))
        #suite.addTest(TestInfer("test_for_and_while"))
        #suite.addTest(TestInfer("test_set"))
        #suite.addTest(TestInfer("test_optional_args"))
        #suite.addTest(TestInfer("test_keyword_args"))
        #suite.addTest(TestInfer("test_complex_args"))
        #suite.addTest(TestWarnings("test_nonexistent_class"))
        #suite.addTest(TestInfer("test_bool_ops"))
        #suite.addTest(TestInfer("test_dict"))
        #suite.addTest(TestInfer("test_set_ops"))
        #suite.addTest(TestInfer("test_set_repr"))
        #suite.addTest(TestInfer("test_num_equal"))
        #suite.addTest(TestInfer("test_tuple"))
        #suite.addTest(TestInfer("test_scope_merging"))
        #suite.addTest(TestInfer("test_break_continue"))
        #suite.addTest(TestInfer("test_inc_dec"))
        #suite.addTest(TestInfer("test_complex_example2"))
        #suite.addTest(TestInfer("test_tuple_assign"))
        
        unittest.TextTestRunner().run(suite)
