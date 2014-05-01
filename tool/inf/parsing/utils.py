import re
import ast
import traceback
from inf.parsing.ply import (
        yacc,
        lex,
        )

import itertools

class Context(object):
    """
    context used for printing parsing tree. Holds information about indentation level and last-seen
    token
    """
    def __init__(self):
        self.indent = 0
        self.last = None
        self.was_newline = False
        self.was_name = False
    
    def get_indent(self):
        return '    ' * self.indent

class Node(object):
    """
    general class for one node in the parsing tree. All nodes but leafs in the parsing tree should
    be of this type; leafs are instances of lex.Token
    """

    def __init__(self, kind, childs=None):
        self.kind = kind
        if not isinstance(childs, yacc.YaccProduction):
            raise Exception('should not get here')
        self.beginLine = -1
        self.endLine = -1
        self.isCompound = False
        self.emptyLines = 0
        self.emptyLinesNums = []
        self.childs = []
        for i in range(1, len(childs)):
            self.childs.append(childs[i])
            if isinstance(childs[i], Node) and ((childs[i].kind == 'block') or childs[i].isCompound):
                self.isCompound = True

            if isinstance(childs[i], lex.LexToken):
                if self.beginLine == -1:
                    self.beginLine = childs[i].lineno
                if self.endLine == -1:
                    self.endLine = childs[i].lineno
                if childs[i].type == 'NEWLINE':
                    count = childs[i].value.count('\n') - 1
                    line = childs[i].lineno
                    self.emptyLines += childs[i].value.count('\n') - 1
                    for i in range(line + 1, line + count + 1):
                        self.emptyLinesNums.append(i)
            else:
                if self.beginLine > childs[i].beginLine or self.beginLine == -1:
                    self.beginLine = childs[i].beginLine
                if self.endLine < childs[i].endLine:
                    self.endLine = childs[i].endLine
                self.emptyLines += childs[i].emptyLines
                self.emptyLinesNums += childs[i].emptyLinesNums

    def __str__(self):
        return self.kind + '[' + str(self.beginLine) + ',' + str(self.endLine) + '],' + str(self.isCompound) + ',' + str(self.emptyLinesNums)
    def __repr__(self):
        return self.__str__()

    def __iter__(self):
        yield self
        for child in self.childs:
            if not isinstance(child, Node):
                yield child
            else:
                for childchild in child:
                    yield childchild

def token_to_str(ctx, token):
    """
    converts token to string, handles special cases such as indent/dedent tokens, etc...
    """
    if token.type == 'INDENT':
        ctx.indent += 1
    elif token.type == 'DEDENT':
        ctx.indent -= 1
    elif token.type == 'NEWLINE':
        return '\n'
    elif token.type == 'DEF':
        return 'def '
    elif token.type == 'CLASS':
        return 'class '
    elif token.type == 'FOR':
        return 'for '
    elif token.type == 'WHILE':
        return 'while '
    elif token.type == 'IF':
        return 'if '
    elif token.type == 'NAME':
        if ctx.last and ctx.last.type == 'NAME':
        #if ctx.last and ctx.last.type != 'NEWLINE':
            return ' ' + token.value
        else:
            return token.value
        '''
    OLD
    elif token.type == 'NUMBER':
        return ' ' + str(token.value[1])
    '''
    elif token.type == 'NUMBER':
        if ctx.last and ctx.last.type != 'NEWLINE':
            return ' ' + str(token.value[1])
        else:
            return token.value[1]
    elif token.type == 'STRING':
        val = token.value
        triple_double = '"""'
        triple_single = "'''"
        if re.search(triple_single, val):
            delim = triple_double
            if re.search(triple_double, val):
                raise Exception('should not get here')
        else:
            delim = triple_single
        return delim + token.value + delim
    elif token.type in ['LPAR', 'RPAR', 'COLON', 'LBRACE', 'RBRACE', 'OPERATOR', 'STRING', 'LSQB', 'RSQB', 'PERIOD', "RANGE", 'COMMENT']:
        return token.value
    elif token.type == 'ENDMARKER':
        pass
    elif True:
        return str(token)

def node_to_tree(node):
    """
    returns string representation of a tree rooted in the given node.
    """
    def _to_tree_string(node, indent=0):
        res = ["  "*indent + str(node) + '\n']
        if hasattr(node, 'childs'):
            for child in node.childs:
                res.extend(_to_tree_string(child, indent + 1))
        return res

    res = _to_tree_string(node)

    return ''.join(res)

def astNode_to_tree(node):
    """
    returns string representation of a ASTree rooted in the given node.
    """
    def _to_tree_string(node, indent=0):
        res = ["\t"*indent + type(node).__name__ + " : " + str(node.__dict__) + '\n']
        for child in ast.iter_child_nodes(node):
            res.extend(_to_tree_string(child, indent + 1))
        return res
    res = _to_tree_string(node)
    
    return ''.join(res)

def node_to_str(node):
    """
    return code-like representation of a tree rooted in a given node. Should be parseable by exec,
    eval or compile builtins.
    """
    ctx = Context()
    def _to_string(node, ctx):
        res = []
        for child in node.childs:
            if isinstance(child, Node):
                res.append(_to_string(child, ctx))
            elif isinstance(child, lex.LexToken):
                if ctx.was_newline and child.type != 'INDENT' and child.type != 'DEDENT':
                    ctx.was_newline = False
                    res.append(ctx.get_indent())
                if child.type == 'NEWLINE':
                    ctx.was_newline = True
                token_string = token_to_str(ctx, child)
                if token_string:
                    res.append(token_string)
                ctx.last = child
            else:
                raise Exception('should not get here! ' + str(child))
        return ''.join(res)
    return _to_string(node, ctx)

def node_to_defs(node):
    """
    returns list of function and class definitions
    """
    ctx = Context()
    def _toList(node, ctx, value):
        res = []
        wasClassOrFunc = value
        if node is not None:
            for child in node.childs:
                if isinstance(child, Node):
                    listOutput, boolValue = _toList(child, ctx, wasClassOrFunc)
                    wasClassOrFunc = boolValue
                    for item in listOutput: 
                        res.append(item)
                elif isinstance(child, lex.LexToken):
                    if child.type == 'CLASS' or child.type == 'DEF':
                        # wasClassOrFunc = True
                        if child.type == 'CLASS':
                            wasClassOrFunc = 'C'
                        else:
                            wasClassOrFunc = 'F'
                    if child.type == 'NAME' and wasClassOrFunc:
                        token_string = token_to_str(ctx, child)
                        if not token_string in res:
                            res.append((token_string, wasClassOrFunc))
                        wasClassOrFunc = None
                else:
                    raise Exception('should not get here! ' + str(child))
        return (res, wasClassOrFunc)
    finalOutput = _toList(node, ctx, False)
    return finalOutput[0]

def traverse_ast(node):
    """
    modifies parsing tree,controls each definition by ast.parse...
    """
    deletedParts = []
    def _ast(node):
        if isinstance(node, Node):
            if (node.kind == 'block'):
                if node.isCompound:
                    for child in node.childs:
                        _ast(child)
                try:
                    n = parse_with_ast(node)
                except Exception as error:
                    print(error)
                    print("DELETING A PART OF CODE")
                    deletedParts.append((node.beginLine, node.endLine))
                    node.childs = []
            else:
                for child in node.childs:
                        _ast(child)        
            
    return (_ast(node), deletedParts)

def traverse_ast_test(node):
    """
    modifies parsing tree,controls each definition by ast.parse...
    """
    deletedParts = []
    def _ast(node):
        if isinstance(node, Node):
            if (node.kind == 'stmt'):
                if node.isCompound:
                    for child in node.childs:
                        _ast(child)
                try:
                    n = parse_with_ast(node)
                except Exception as error:
                    traceback.print_exc()
                    print("ERROR:"+str(error))
                    print("NODE:"+node_to_str(node))
                    print("DELETING A PART OF CODE")
                    deletedParts.append((node.beginLine, node.endLine))
                    node.childs = []
            else:
                for child in node.childs:
                        _ast(child)       
            
    return (_ast(node), deletedParts)

def parse_with_ast(node):
    """
    returns abstract syntax tree(or exception) of a tree rooted in the given node.
    """
    code = node_to_str(node)
    return ast.parse(code)

def getOriginLineNum(lineNum, delLines):
    for delLine in delLines:
        if delLine <= lineNum:
            lineNum += 1
    return lineNum

def getCurrentLineNum(lineNum, delLines):
    delLines.sort(reverse=True)
    for delLine in delLines:
        if delLine <= lineNum:
            lineNum -= 1
    return lineNum

def findAstNodeAtLine(lineNum, node):
    def _astNodeAtLine(lineNum, node):
        result = None
        if hasattr(node, 'lineno') and node.lineno == lineNum:
            result = node
        for child in ast.iter_child_nodes(node):
            if result is None:
                result = _astNodeAtLine(lineNum, child)
        return result
    return _astNodeAtLine(lineNum, node)

'''
Returns string representation of object on which autocomplete have been called.
'''
def getObjectStringFromLine(lineText):
    # parts = re.split('\[|\]|\(|\)',lineText)
    # parts = re.split('=', lineTextNoWhiteSpace)
    lineTextNoWhiteSpace = lineText.replace(' ', '').strip('.')
    result = ''
    bracketCounter = 0
    squareBracketCounter = 0
    curlyBracketCounter = 0
    for c in reversed(lineTextNoWhiteSpace):
         if ( c == ',' or  c == ':' or c == '=')  and bracketCounter == 0 and curlyBracketCounter == 0 and squareBracketCounter == 0:
             break
         
         if c == '(':
             if bracketCounter == 0:
                 break
             else:
                 bracketCounter -= 1
         elif c == '[':
             if squareBracketCounter == 0:
                 break
             else:
                 squareBracketCounter -= 1
         elif c == '{':
             if curlyBracketCounter == 0:
                 break
             else:
                 curlyBracketCounter -= 1
         elif c == ')':
             bracketCounter += 1
         elif c == ']':
             squareBracketCounter += 1
         elif c == '}':
             curlyBracketCounter += 1  
         #else re.match('[a-zA-Z0-9_.]', c):
         
         result = c + result
    return result

'''
Returns s
'''
def prepareAutocomplete (lineNum, delLines, lineText, ast_rep):
    currLineNo = getCurrentLineNum(lineNum, delLines)
    nodeOnGivenLine = findAstNodeAtLine(currLineNo, ast_rep)
    objectString = getObjectStringFromLine(lineText)
    # print(astNode_to_tree(nodeOnGivenLine))
    # print('----')
    # print('Autocomplete on: '+ str(objectString))
    return (nodeOnGivenLine, objectString)

def Ast_eq(node1, node2):
    return ast.dump(node1) == ast.dump(node2)

