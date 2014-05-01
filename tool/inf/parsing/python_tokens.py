import re

# String literal from Python's Grammar/Grammar file to tokenization name
literal_to_name = {}

# List of tokens for PLY
tokens = []

kwlist=['class', 'def', 'if', 'else', 'elif', 'try', 'except', 'finally', 'while', 'for', 'with']
RESERVED = {}
for literal in kwlist:
    name = literal.upper()
    RESERVED[literal] = name
    literal_to_name[literal] = name
    tokens.append(name)

# These are sorted with 3-character tokens first, then 2-character then 1.
#LSQB [
#RSQB ]
for line in """
COLON :

# The PLY parser replaces these with special functions
LPAR (
RPAR )
LBRACE {
RBRACE }
LSQB [
RSQB ]
""".splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    name, literal = line.split()
    literal_to_name[literal] = name
    if name not in tokens:
        tokens.append(name)  # N**2 operation, but N is small

    ## Used to verify that I didn't make a typo
    #if not hasattr(tokenize, name):
    #    raise AssertionError("Unknown token name %r" % (name,))

    # Define the corresponding t_ token for PLY
    # Some of these will be overridden
    t_name = "t_" + name
    if t_name in globals():
        globals()[t_name] += "|" + re.escape(literal)
    else:
        globals()[t_name] = re.escape(literal)

# Delete temporary names
del t_name, line, name, literal



