class object:

    def __init__(self):
        pass

    def __getattr__(self, name):
        return inf_getattr(self, name)

    def __setattr__(self, name, value):
        return inf_setattr(self, name, value)

class TypeContainer(object):
    def __init__(self,T):
        self.T=T

class ProblemException(object):
    def __init__(self, error, message=None, symbol=None):
        self.error = error
        self.message = message
        self.symbol = symbol

class Exception(object):
    pass

class PlaceHolder(object):
    pass

class StopIteration(Exception):
    pass

class inf_slice(object):
    def __init__(self,x=None,y=None,z=None):
        self.start = x
        self.end = y
        self.step = z

class num(object):
    
    def __add__(self,x):
        if isinstance(x,num) or isinstance(x,bool):
            return TypeContainer(num)
        else:
            return ProblemException(x)

    def __div__(self,x):
        if isinstance(x,num) or isinstance(x,bool):
            return TypeContainer(num)
        else:
            return ProblemException(x)

    def __mul__(self,x):
        if isinstance(x,num) or isinstance(x,bool):
            return TypeContainer(num)
        else:
            return ProblemException(x)
    
    def __sub__(self,x):
        if isinstance(x,num) or isinstance(x,bool):
            return TypeContainer(num)
        else:
            return ProblemException(x)
    
    def __pos__(self):
        return self
    
    def __neg__(self):
        return self
    
    def __invert__(self):
        return self
    
    def __eq__(self,x):
        if isinstance(x,num) or isinstance(x,bool):
            return inf_equal(self, x)
        else:
            return ProblemException(x,message='operands are not the same type')
    
    def __lt__(self,x):
        if isinstance(x,num):
            return TypeContainer(bool)
        if isinstance(x,bool):
            return TypeContainer(bool)
        return ProblemException(x)
    
    def __gt__(self,x):
        if isinstance(x,num):
            return TypeContainer(bool)
        if isinstance(x,bool):
            return TypeContainer(bool)
        return ProblemException(x)

class int(num):
    def __init__(self,x=None):
        #return TypeContainer(num)
        pass
class float(num):
    def __init__(self,x):
        #return TypeContainer(num)
        pass
class bool(object):
    def __init__(self,x=None):
        if x:
            return True
        return False
        #return TypeContainer(bool)

class str(object):
    def __init__(self,x=None):
        #return TypeContainer(str)
        pass
    def __add__(self,x):
        if isinstance(x,str):
            return TypeContainer(str)
        else:
            return ProblemException(x)
        
    def __lt__(self,x):
        if isinstance(x,str):
            return TypeContainer(bool)
        return ProblemException(x)
    
    def __gt__(self,x):
        if isinstance(x,str):
            return TypeContainer(bool)
        return ProblemException(x)
    
    def __iter__(self):
        return inf_iterator(self)

class inf_iterator(object):
    def __init__(self,data):
        self.inf_data = data
    
    def __iter__(self):
        return self
    
    def __next__(self):
        return self.inf_data

class inf_list(object):
    
    def __init__(self):
        self.inf_r = PlaceHolder()
       
    def append(self, new_item):
        if isinstance(self.inf_r,PlaceHolder):
            self.inf_r = new_item
        else:
            if inf_random():
                self.inf_r = new_item
                
    def __getitem__(self,key):
        if isinstance(key,num):
            return self.inf_r
        return ProblemException(key,message='List indices must be integers')
    
    def __setitem__(self,key,value):
        if isinstance(key,num):
            self.append(value)
        else:
            return ProblemException(key,message='List indices must be integers')
    
    def __iter__(self):
        return inf_iterator(self.inf_r)
    
    def reverse(self):
        return self
    
    def sort(self):
        return self

class inf_dict(object):
    def __init__(self):
        self.inf_keyR = PlaceHolder()
        self.inf_valueR = PlaceHolder()
    
    def __getitem__(self,key):
        if isinstance(self.inf_valueR,PlaceHolder):
            return ProblemException(self)
        return self.inf_valueR
    
    def __setitem__(self,key,value):
        if isinstance(self.inf_keyR,PlaceHolder):
            self.inf_keyR=key
            self.inf_valueR=value
        else:
            if inf_random():
                self.inf_keyR=key
                self.inf_valueR=value
    
    def __iter__(self):
        return inf_iterator((self.inf_keyR,self.inf_valueR))
    
    def append(self, key, value):
        if self.inf_keyR is None:
            self.inf_keyR=key
            self.inf_valueR=value
        else:
            if inf_random():
                self.inf_keyR=key
                self.inf_valueR=value
        
    def update(self,other):
        if inf_random():
            self.inf_keyR=other.inf_keyR
            self.inf_valueR=other.inf_valueR
            
class inf_tuple(object):
    def __init__(self):
        self.inf_item1=PlaceHolder()
        self.inf_item2=PlaceHolder()
        self.inf_item3=PlaceHolder()
        self.inf_item4=PlaceHolder()
        self.inf_item5=PlaceHolder()
    
    def __getitem__(self,key):
        if isinstance(key,num):
            if key==0:
                return self.inf_item1
            if key==1:
                return self.inf_item2
            if key==2:
                return self.inf_item3
            if key==3:
                return self.inf_item4
            if key==4:
                return self.inf_item5
            #mozno vratit placeholder???
            #return self.item1
            return PlaceHolder()
        if isinstance(key,inf_slice):
            return self
        return ProblemException(key)
    
    def inf__setitem__(self,key,value):
        if not isinstance(value,PlaceHolder):
            if isinstance(key,num):
                if key==0:
                    self.inf_item1=value
                if key==1:
                    self.inf_item2=value
                if key==2:
                    self.inf_item3=value
                if key==3:
                    self.inf_item4=value
                if key==4:
                    self.inf_item5=value
            elif isinstance(key,inf_slice):
                pass    
            else:
                return ProblemException(key)
    
    def __iter__(self):
        #handle in parse_ast
        pass
            
    def __add__(self,other):
        if not isinstance(other,inf_tuple):
            return ProblemException(other)
        return (self.inf_item1,self.inf_item2,self.inf_item3,self.inf_item4,self.inf_item5,other.inf_item1,other.inf_item2,other.inf_item3,other.inf_item4,other.inf_item5)
    
class inf_set(object):
    def __init__(self):
        self.inf_r = PlaceHolder()
        
    def add(self,new_item):
        if isinstance(self.inf_r,PlaceHolder):
            self.inf_r = new_item
        else:
            if inf_random():
                self.inf_r = new_item
    
    def pop(self):
        return self.inf_r
    
    def __iter__(self):
        return inf_iterator(self.inf_r)

    def union(self, other):
        if inf_random():
            return self
        return other
    def bitAnd(self, other):
        pass
    def difference(self, other):
        pass
    def symetricDifference(self, other):
        pass

def isinstance(a,b):
    pass

def type(a):
    pass

def inf_random():
    pass

def inf_is(a,b):
    pass

def inf_isnot(a,b):
    if inf_is(a,b):
        return False
    return True

def id(a):
    return TypeContainer(num)

def inf_len(arg):
    return arg.__len__()
#inf_len.original_name="len"

def inf_getattr(obj, name):
    pass

def inf_setattr(obj, name, value):
    pass

def print(object):
    pass

def range(a,b):
    pass

def inf_equal(a,b):
    pass

def __and__(a,b):
    if a:
        return b
    else:
        return a

def __or__(a,b):
    if a:
        return a
    else:
        return b
    
def __not__(a):
    if a:
        return False
    return True

def hasattr(object, name):
    if isinstance(name,str):
        return inf_hasattr(object, name)
    return ProblemException(name, message='attribute name must be a string')

def inf_hasattr(object, name):
    pass

def list(a):
    if hasattr(a,'__iter__'):
        return [a.__iter__().__next__()]
    return ProblemException(a, message='object is not iterable')
def set(a):
    if hasattr(a,'__iter__'):
        return (a.__iter__().__next__(),)
    return ProblemException(a, message='object is not iterable')
def dict(a):
    if hasattr(a,'__iter__'):
        x = a.__iter__().__next__()
        return {x:x}
    return ProblemException(a, message='object is not iterable')
def tuple(a):
    if hasattr(a,'__iter__'):
        return (a.__iter__().__next__(),)
    return ProblemException(a, message='object is not iterable')
#def str(a):
#    return TypeContainer(str)
#def int(a):
#    return TypeContainer(num)
#def bool(a):
#    return TypeContainer(bool)

str.__name__ = "str"
num.__name__ = "num"
bool.__name__ = "bool"

