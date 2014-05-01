from inf.parsing.ply import yacc
from inf.parsing.utils import Node

import inf.parsing.python_lexer as python_lexer

tokens = python_lexer.tokens



"""
parser ludskou recou:
    fragment: nejake hocico v jednom riadku
    stmt: fragment NEWLINE | classdef | funcdef | block
    suite: hocikolko stmt 
    indented_suite: INDENT suite DEDENT
    classdef: DEF stmt: NEWLINE indented_suite
    funcdef: DEF stmt: NEWLINE indented_suite
"""

def p_file_input(p):
    '''
    file_input : suite ENDMARKER
    '''
    p[0] = Node(kind='file_input', childs=p)

def p_block(p):
    '''
    block : block_keyword fragment COLON NEWLINE INDENT suite DEDENT
    '''
    p[0] = Node(kind='block', childs=p)

def p_inline_block(p):
    '''
    block : block_keyword fragment COLON suite 
    '''
    p[0] = Node(kind='block', childs=p)

   
def p_empty_block(p):
    '''
    block : block_keyword fragment COLON NEWLINE 
    '''
    p[0] = Node(kind='block', childs=p)

def p_block_keyword(p):
    '''
    block_keyword : CLASS
                    | DEF
                    | IF
                    | ELIF
                    | ELSE
                    | TRY
                    | EXCEPT
                    | FINALLY
                    | WITH
                    | WHILE
                    | FOR
    '''
    p[0] = Node(kind='keyword', childs=p)

def p_suite(p):
    '''
    suite : stmt
          | suite stmt 
    '''
    p[0]=Node(kind='suite', childs=p)

def p_stmt(p):
    '''
    stmt : fragment NEWLINE
         | fragment
         | NEWLINE         
         | block
    '''
    p[0]=Node(kind='stmt', childs=p)


def p_fragment(p):
    '''
    fragment : fragment LBRACE
         | fragment RBRACE
         | fragment STRING_END
         | fragment STRING_CONTINUE
         | fragment STRING
         | fragment STRING_START_TRIPLE
         | fragment WS 
         | fragment STRING_START_SINGLE
         | fragment NUMBER
         | fragment NAME
         | fragment LPAR
         | fragment RPAR
         | fragment OPERATOR
         | fragment LSQB
         | fragment RSQB
         | fragment COLON
         | fragment block_keyword
         | fragment PERIOD
         | fragment RANGE
         | block_keyword
         | LBRACE
         | RBRACE
         | STRING_END
         | STRING_CONTINUE
         | STRING
         | STRING_START_TRIPLE
         | WS 
         | STRING_START_SINGLE
         | NUMBER
         | NAME
         | LPAR
         | RPAR
         | LSQB
         | RSQB
         | COLON
         | OPERATOR
         | COMMENT
         | RANGE
    '''
    p[0]=Node(kind='fragment', childs=p)
    


# def p_advice_fragment(p):
#     '''
#     fragment : NAME PERIOD
#     '''
#     p[2].value='.GiveMeAdvice'
#     p[0]=Node(kind='fragment',childs=p)
#      
# def p_adviceRec_fragment(p):
#     '''
#     fragment : fragment NAME PERIOD
#     '''
#     p[3].value='.GiveMeAdvice'
#     p[0]=Node(kind='fragment',childs=p)
#      
# def p_nonAdvice_fragment(p):
#     '''
#     fragment : NAME PERIOD NAME
#     '''
#     p[0]=Node(kind='fragment',childs=p)
#      
# def p_nonAdviceRec_fragment(p):
#     '''
#     fragment : fragment NAME PERIOD NAME
#     '''
#     p[0]=Node(kind='fragment',childs=p)

class RobustParserError(Exception):
    def __init__(self, data):
        self.data = data
        

def p_error(e):
    #print("TOTO SA ZAVOLALO")
    #print(dir(e))
    #print("CISLO RIADKA: "+str(e.lineno))
    print('error: %s'%e)
    if hasattr(e, 'lineno'):
        #return e.lineno
        raise RobustParserError(e)
    
def parse_data(data,lexer):
    yacc.yacc(debug=1)
    result = yacc.parse(data, lexer)
    return result



