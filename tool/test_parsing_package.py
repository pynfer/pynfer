import inf.parsing.python_lexer as python_lexer
import inf.parsing.python_parser as parser
import inf.parsing.utils as utils
import unittest
import logging
import re
import random


def setup_test(test, filename):
    print("--------------------",test)
    f = open('inf/parsing/'+filename)
    data = f.read()
    f.close()
    gl={}
    lc={}
    lexer = python_lexer.PythonLexer()
    lexer.input(data)
    res=parser.parse_data(data, lexer)
    
    code=utils.node_to_str(res)
    anotherTest = utils.node_to_defs(res)
    test.gl=gl
    test.lc=lc
    test.code=code
    test.node=res
    

class SampleTest(unittest.TestCase):

    def test_sample1(self):
        setup_test(self, 'samples/sample1.py')
        lc=self.lc
        exec(self.code,self.gl,self.lc)
        pokus=lc['Pokus']()
        a=lc['a']
        b=lc['b']
        mul=lc['mul']

        self.assertEqual(pokus.get_all(), (10,10,10))
        self.assertEqual(a, 'jozo')
        self.assertEqual(b, 23)
        self.assertEqual(mul(4)(5), 20)
        self.assertTrue(re.search('riadkov', pokus.__init__.__doc__))
        
        utils.traverse_ast(self.node)
        self.assertEqual(self.code, utils.node_to_str(self.node))

    
    def test_sample2(self):
        setup_test(self, 'samples/sample2.py')
        exec(self.code,globals(),self.lc)
        lc=self.lc
        dct=lc['get_dct']()
        self.assertEqual(dct[3],4)
        tpl=lc['get_tpl']()
        lst=lc['lst']
        slc=lc['slc']
        self.assertEqual(len(tpl),5)
        self.assertEqual(len(lst),5)
        self.assertEqual(len(slc),2)

    def test_sample3(self):
        setup_test(self, 'samples/sample3.py')
        print(self.code)
        exec(self.code,globals(),self.lc)
        #print(utils.node_to_tree(self.node))
        lc=self.lc
        inc=lc['inc']
        self.assertEqual(inc(3),4)
        self.assertIn('pokus', lc)
        self.assertEqual(lc['loop'](),10)
        self.assertLess(lc['cond'](),0.001)
    
    def test_sample4(self):
        f = open('inf/parsing/samples/sample4_solution.py')
        data = f.read()
        f.close()
        setup_test(self, 'samples/sample4.py')
        utils.traverse_ast(self.node)
        self.assertEqual(data, utils.node_to_str(self.node))
    
    def test_sample5(self):
        f = open('inf/parsing/samples/sample5_solution.py')
        data = f.read()
        f.close()
        setup_test(self, 'samples/sample5.py')
        utils.traverse_ast(self.node)
        self.assertEqual(data, utils.node_to_str(self.node))
        
        
    def test_sample6(self):
        setup_test(self, 'samples/sample8.py')
        lc = self.lc
        exec(self.code,self.gl,self.lc)
        square=lc['Square'](50)
        
        self.assertEqual(square.area(),2500)

class TestLineNums(unittest.TestCase):

    def test_lineNums(self):
        delParts = [5,6,7,8,9,13,14,15,16,17]
        num = utils.getOriginLineNum(6, delParts)
        num1 = utils.getOriginLineNum(10, delParts) 
        self.assertEqual(num,11)
        self.assertEqual(num1,20)
        
        
        

if __name__ == '__main__':
    logger=logging.getLogger('')
    logger.setLevel(logging.DEBUG)
    unittest.main()





#print(utils.node_to_tree(res))
#for tok in lexer:
#    print(tok.__str__())

#if __name__ == '__main__':
#    run_all=True
#    #run_all=False
#
#    if run_all:
#        logger=logging.getLogger('')
#        logger.setLevel(logging.DEBUG)
#        unittest.main()
#    else:
#        suite = unittest.TestSuite()
#        suite.addTest(TestWarnings('test_nonexistent_attribute'))
#        suite.addTest(TestScope('test_basic'))
#        suite.addTest(TestScope('test_parent'))
#        suite.addTest(TestScope('test_copy'))
#        unittest.TextTestRunner().run(suite)
