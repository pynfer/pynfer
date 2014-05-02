import sys
import ast
from inf.inference.parse_ast import Problem
from inf.inference.parse_ast import FinalParser

'''
Exception that reports the wrong number of system args
'''
class InvalidArgsException(Exception):
    pass


'''
This function returns user friendly string representation of Problem instance
'''
def pretty_str(problem, importance='E'):
    return "Line %d - %s - %s  - %s"%(problem.node.lineno, importance, problem.message, str(problem.symbol))


'''
Main of RunAnalysis
'''
path = None
count_iterations = None

try:
    if len(sys.argv) == 2:
        path = sys.argv[1]
    elif len(sys.argv) == 3:
        path = sys.argv[1]
        count_iterations = sys.argv[2]
    else:
        raise InvalidArgsException()
    
    f = open(path,'r')
    data = f.read()

    abs_syn_tree = ast.parse(data)
    if count_iterations is None:
        final_parser = FinalParser()
    else:
        final_parser = FInalParser(count_iterations)
    
    final_parser.eval_in_root(abs_syn_tree)
    if len(final_parser.problems)==0 and len(final_parser.warnings)==0:
        print('No errors were detected')
    else:
        print('Following errors were detected:')
        rows = []
        for p in final_parser.problems:
            print(pretty_str(p))
        for w in final_parser.warnings:
            print(pretty_str(w,'W'))

except SyntaxError as e:
    print("%s contains syntactical errors!"%(sys.argv[1].split('/')[-1]))
    print(str(e))
    
except InvalidArgsException as e:
    print("Wrong number of arguments, %d given, 3 expected"%(len(sys.argv)))
    
except IOError as e:
    print("Could not find/open the given Python file!")

except Exception as e:
    print(str(e))
    print("Sorry, something went wrong. It hurts!")
    
    
