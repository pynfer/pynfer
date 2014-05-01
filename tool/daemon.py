'''
Created on 2.11.2013

Last updated on: 11.4.2014

@author: Bc. Lubomir Zak 

Faculty of mathematics, physics and informatics

Comenius University, Bratislava
'''

import socket
import select
import sys
import traceback
import inf.parsing.utils
import asyncore
import collections
import logging
import threading
import os
import time
import json

from inf.parsing import python_lexer
from inf.parsing import python_parser
from inf.parsing import utils
from inf.inference.parse_ast import Problem
from inf.inference.parse_ast import Parser
from inf.inference.parse_ast import FinalParser
from inf.inference.typez import (
        Scope,
        Typez,
        none_type
        )

'''
Some small helping functions
'''
def string_to_buffer(incomingString):
    return incomingString.splitlines()
    
def buffer_to_string(buffer):
    result = ""
    for line in buffer:
        result += line + "\n"
    return result

def log_to_file(stringToLog):
    print(stringToLog)
    #from time import gmtime, strftime
    #time = strftime("%Y-%m-%d %H:%M:%S", gmtime())
    #f = open("serverLog.txt", "a")
    #f.write(time + ": "+ stringToLog + "\n")
    #f.close()

def log_time(msg, current_time, start_time):
    log_to_file(msg + str(current_time - start_time))
'''
Main methods which host calls according to request received
'''
    
def get_auto_completion(host, client_address, buffer_used, variable_line, line_number):
    '''
    This method is called when user presses '.' symbol.
    
    We want to find all possible attributes for given symbol on given buffer at given line.
    
    Call eval_in_root plus send nodeAst - means evaluation will stop once given node is reached.
    '''
    try:
        #Get leading spaces so the indent matches current level
        variable_line = variable_line.replace('\t', '    ')
        leading_spaces = len(variable_line) - len(variable_line.lstrip())
        
        # Get only relevant part of line
        line_modified = utils.getObjectStringFromLine(variable_line)
        
        # Replace given line with string which will be resolved - much easier for our solution
        resolving_name = 'target_for_completion'
        buffer = buffer_used
        buffer[line_number - 1] = variable_line[0:leading_spaces] + resolving_name + ' = ' + line_modified
    
        # Parse modified buffer and eval 
        #ast_rep, del_lines = completion_parse(buffer)
        data = buffer_to_string(buffer)
        lexer = python_lexer.PythonLexer()
        lexer.input(data)
        lexer = python_lexer.PythonLexer()
        res = python_parser.parse_data(data,lexer)
        
        tree, del_parts = utils.traverse_ast_test(res)
        ast_tree = utils.parse_with_ast(res)  
        
        del_lines = []
        for delPart in del_parts:
            for i in range(delPart[0],delPart[1]+1):
                del_lines.append(i) 
        
        del_lines+=res.emptyLinesNums
        temp={line for line in del_lines}
        del_lines = [line for line in temp]
        del_lines.sort()
        
        current_line_number = utils.getCurrentLineNum(line_number, del_lines)

        parser = FinalParser(1)
        parser.eval_in_root(ast_tree, current_line_number + 1)
        
        #print(str(parser.scopes[0]))
        
        #Remove inf_ attribtues since those are used for internal purposes
        list_of_all = parser.get_all_possible_attr(resolving_name)
        reduced_list = []
        for item in list_of_all:
            if not item[0].startswith('inf_'):
                reduced_list.append(item)
        
        # Respond to the client.
        response_completion = json.dumps({'options' : reduced_list})
        host.respond(bytes(response_completion, 'UTF-8'), client_address)
    except:
        traceback.print_exc()
        # Send an empty list if any error occurred
        list_for_completion = []
        response_completion_error = json.dumps({'options' : list_for_completion})
        host.respond(bytes(response_completion_error, 'UTF-8'), client_address)

def parse_and_validate(host, dictionaryID, client_address, number_of_iterations):
    """
    Main method which evaluates whole code and sends respond with errors and warnings.
    """
    try:
        start_time = time.time() * 1000
        log_to_file("START OF VALIDATION: "+str(start_time)+", Number of iterations: "+str(number_of_iterations))
        
        #buffer = buffer_used
        buffer = openBuffers[dictionaryID]
        
        problems_list = []
        warnings_list = []        
        
        # Decode the data
        data = buffer_to_string(buffer)
        lexer = python_lexer.PythonLexer()
        lexer.input(data)
        
        #for token in lexer:
        #    print(token.value)
            
        lexer = python_lexer.PythonLexer()
        res = python_parser.parse_data(data,lexer)
        log_time("AFTER PARSE DATA: ", time.time() * 1000, start_time)
        
        tree, del_parts = utils.traverse_ast_test(res)       
        log_time("AFTER TRAVERSE AST: ", time.time() * 1000, start_time)  
        
        ast_tree = utils.parse_with_ast(res)   
        log_time("AFTER PARSE WITH AST: ", time.time() * 1000, start_time)
        
        parser=FinalParser(number_of_iterations)
        parser.eval_in_root(ast_tree)
        del_lines = []
        for delPart in del_parts:
            for i in range(delPart[0],delPart[1]+1):
                del_lines.append(i)
                      
        log_time("AFTER EVAL IN ROOT: ", time.time() * 1000, start_time)
        
        #processing syntax problems
        for line in del_lines:
            p = []
            p.append(line)
            p.append('Invalid syntax OOOo.')
            problems_list.append(p)
            
        del_lines+=res.emptyLinesNums
        temp={line for line in del_lines}
        del_lines = [line for line in temp]
        del_lines.sort()
        
        list_of_used_lines = []
        
        #Problems
        for problem in parser.problems:   
            if not hasattr(problem.node, 'processed'):
                problem.node.lineno=utils.getOriginLineNum(problem.node.lineno,del_lines)        
                problem.node.processed=1

            if not (problem.node.lineno in list_of_used_lines):
                b = []
                b.append(problem.node.lineno)
                b.append(str(problem))
                problems_list.append(b)
                list_of_used_lines.append(problem.node.lineno)
                
        #Warnings
        for warning in parser.warnings:
            if not hasattr(warning.node, 'processed'):
                warning.node.lineno=utils.getOriginLineNum(warning.node.lineno,del_lines)        
                warning.node.processed=1
            w = []
            w.append(warning.node.lineno)
            w.append(str(warning))
            warnings_list.append(w)
        
        problems = json.dumps({'problems' : problems_list, 'warnings' : warnings_list})
        print("DUMPED THING: "+str(problems))
        host.respond(bytes(problems, "UTF-8"), client_address)
        
        
        host.validationRunning = False
        log_to_file('----------------------------')
        
    except IndentationError as error:
        log_to_file("Indentation error in parsing.")
        traceback.print_exc()
        
        indent_error = json.dumps({'message' : error.msg, 'line_number' : error.lineno})
        host.respond(bytes(indent_error,"UTF-8"), client_address)
        
        host.validationRunning = False
    except python_parser.RobustParserError as error:
        log_to_file("Error in parsing: returning correct line number.")
        
        b = []
        b.append(error.data.lineno)
        b.append("invalid syntax")
        problems_list.append(b)
        
        problems = json.dumps({'problems' : problems_list, 'warnings' : warnings_list})
        host.respond(bytes(problems, "UTF-8"), client_address)
        host.validationRunning = False
    except Exception as error:
        log_to_file("Error in parsing: ")
        traceback.print_exc()
        #connection.sendall(bytes("endOfValidation: "+error, "utf-8"))
        #host.respond(bytes("endOfValidation", "utf-8"), client_address)
        error_problems_response = json.dumps({'problems' : [], 'warnings' : []})
        host.respond(bytes(error_problems_response, "UTF-8"), client_address)
        host.validationRunning = False

"""
Methods for holding info about whole project - all function definitions and classes 
including nicely recalculating current buffer data on each requests.

We hold information about project definitions in the following format:
[{'name of func/class' : ('F'/'C', 'location paths')}]
eg. list of dictionaries, where the key is name of function or class and value is tuple
containing one letter (F or C) on position 0 and location of definition on position 1 
"""
def recalculate_definitions(dictOfFuncsAndClasses, clientInitPath):
    while True:
        time.sleep(300)
        log_to_file("Recalculating projects information BEGIN...")
        for key in dictOfFuncsAndClasses.keys():
            log_to_file("Iterating trough files...")
            initFileLocation = key
            finalDirectory = initFileLocation[initFileLocation.rfind('/'):]
            finalRes = iterate_all_on_given_path(initFileLocation, finalDirectory)
            
            # Update it
            final_res_sorted = sort_final_dictionary(finalRes)
            tempDict = {initFileLocation : final_res_sorted}
            #TODO: testing
            dictOfFuncsAndClasses.pop('initFileLocation', None)
            dictOfFuncsAndClasses.update(tempDict)
            
        log_to_file("Recalculating projects information END...")
        
def respond_definitions(host, client_address, dictionaryID, fullpath, filename):
    try:        
        print("FULLPATH: "+str(fullpath))
        if dictionaryID in clientInitPath.keys() and clientInitPath[dictionaryID] in dictOfFuncsAndClasses.keys():
            listOfOptions = dictOfFuncsAndClasses[clientInitPath[dictionaryID]]
        else: 
            listOfOptions = []
        
        #Recalculate options for current file since the data might have changed
        if dictionaryID in openBuffers.keys():
            print("CLIENT INIT PATH:"+str(clientInitPath))
            if dictionaryID in clientInitPath.keys():
                project_init_path = clientInitPath[dictionaryID]
            else:
                project_init_path = fullpath
                temp_client = {dictionaryID : project_init_path}
                clientInitPath.update(temp_client)
                
            buffer_data = openBuffers[dictionaryID]
            upmost_directory = project_init_path[project_init_path.rfind('/'):]
            listOfOptions = update_given_file_only(listOfOptions, fullpath, upmost_directory, filename, buffer_data)
            
            final_res_sorted = sort_final_dictionary(listOfOptions)
            tempDict = {project_init_path : final_res_sorted}
            dictOfFuncsAndClasses.update(tempDict)
            
        listOfOptions = dictOfFuncsAndClasses[clientInitPath[dictionaryID]]
        
        user_completion_response = json.dumps({'options' : listOfOptions})
        print("DUMPED: "+str(user_completion_response))
        host.respond(bytes(user_completion_response, 'UTF-8'), client_address)
    except:
        traceback.print_exc()
        list_for_def_completion = []
        response_def_completion_error = json.dumps({'options' : list_for_def_completion})
        host.respond(bytes(response_def_completion_error,'UTF-8'), client_address)

def get_all_definitions_at_init(initPathDict, dictionary, rootFilenamesDictionary, directory, dictionaryID, root_filename):
    '''
    Function is used to get all function and class defitions in given project.
    Project is being found like this: try to find __init__ file in currenct directory.
    If it's there, go up and up and try to find upmost __init__. If there's no init, do nothing.
    '''
    try:
        # always update this accordingly to the request
        temp_dict_root = {dictionaryID : root_filename}
        rootFilenamesDictionary.update(temp_dict_root)
        
        if dictionaryID in initPathDict:
            initFileLocation = initPathDict[dictionaryID]
        else:
            initFileLocation = find_init_file(directory, root_filename)
            if initFileLocation is not None:
                tempDict = {dictionaryID : initFileLocation}
                initPathDict.update(tempDict) # save found value
            
        if initFileLocation is not None:
            if initFileLocation in dictionary:
                log_to_file("No need to iterate trough files again, data is valid...")
                finalRes = dictionary[initFileLocation]
            else:
                log_to_file("Iterating trough files...")
                finalDirectory = initFileLocation[initFileLocation.rfind('/'):]
                finalRes = iterate_all_on_given_path(initFileLocation, finalDirectory)
                    
            final_res_sorted = sort_final_dictionary(finalRes)
            tempDict = {initFileLocation : final_res_sorted}
            dictionary.update(tempDict)
        log_to_file('All definitions found...')    
    except Exception as msg:
        traceback.print_exc()
        log_to_file("Error in get_all_definitions_at_init: "+str(msg))
        
def find_init_file(directory, init_file = '__init__.py'):
    '''
    Function returns location of __init__ file recursively searching backwards from given directory
    '''
    print("Locating init_file: "+str(init_file))
    initFile = init_file
    upmost_init_location = None
    f = []
    
    for (dirpath, dirnames, filenames) in os.walk(directory):
        f.extend(filenames)
        break
    
    #print("f: "+str(f))
    
    if initFile in f:
        upmost_init_location = directory
    
    parentDirectory = os.path.abspath(os.path.join(directory, os.pardir))
    
    if parentDirectory is not None and parentDirectory != '/':
        output = find_init_file(parentDirectory,initFile)
        if output is not None:
            upmost_init_location = output
        
    return upmost_init_location

def iterate_all_on_given_path(path, rootDirectory, extension = '.py'):
    '''
    Function iterates recursively trough all .py files under given root directory and 
    appends results to the list
    '''
    finalRes = []
    f = []
    d = []
    for (dirpath, dirnames, filenames) in os.walk(path):
        f.extend(filenames)
        d.extend(dirnames)
        break
    
    #Recursively call this function on all subdirectories
    for dir in d:
        recursiveOutput = iterate_all_on_given_path(path+'/'+str(dir), rootDirectory)
        for item in recursiveOutput: 
            finalRes.append(item)
    
    #Iterate all .py files in f    
    for file in f:
        if str(file).endswith(extension):
            try:
                myfile = open(path + '/' + str(file))
                
                data = myfile.read()
                lexer = python_lexer.PythonLexer()
                lexer.input(data)
                
                res = python_parser.parse_data(data,lexer)
                defAndClass = utils.node_to_defs(res)
                
                if defAndClass is not None:
                    for item in defAndClass:
                        checkExistence = findDictByKeyInListOfDicts(item[0], finalRes)
                        if checkExistence is None:
                            curLocation = path[path.rfind(rootDirectory):]
                            newItem = { item[0] : (item[1], str(curLocation)+'/'+str(file))}
                            finalRes.append(newItem)
                        else:
                            finalRes.remove(checkExistence)
                            oldValue = checkExistence[item[0]]
                            curLocation = path[path.rfind(rootDirectory):]
                            newValue = (item[1], oldValue[1] + ','+ str(curLocation)+'/'+str(file))
                            newItem = { item[0] : newValue}
                            finalRes.append(newItem)
            except Exception as error:
                #print("Iterate error "+str(error))
                pass
    return finalRes

def findDictByKeyInListOfDicts(key, list):
    for item in list:
        if key in item:
            return item
    return None

def sort_final_dictionary(list_of_dictionaries):
    '''
    Sorts list of dictionaries
    '''
    temp = list_of_dictionaries
    temp_keys = []
    # iterate trough list of dictionaries and grab keys from each
    for item in list_of_dictionaries:
        key = item.keys()
        for i in key:
            temp_keys.append(i) 
    # sort keys ignoring case (that's what lambda function is used for)
    temp_keys.sort(key=lambda s: s.lower())
    sorted_list = []
    
    #once we have sorted keys we can append each of the original items
    #in correct order to the output list of dictionaries.
    for item in temp_keys:
        sorted_list.append(findDictByKeyInListOfDicts(item, temp))
    return sorted_list

def update_given_file_only(current_list, path, rootDirectory, file, given_buffer_data):
    '''
    Same as iterate all on given path except this function iterates trough
    given buffer and appends these results to the output - especially useful
    since user might change stuff and then he wants correct feedback.
    '''

    finalRes = current_list
    
    data = buffer_to_string(given_buffer_data)
    lexer = python_lexer.PythonLexer()
    lexer.input(data)
    
    res = python_parser.parse_data(data,lexer)
    defAndClass = utils.node_to_defs(res)
    
    if defAndClass is not None:
        for item in defAndClass:
            checkExistence = findDictByKeyInListOfDicts(item[0], finalRes)
            if checkExistence is None:
                curLocation = path[path.rfind(rootDirectory):]
                newItem = { item[0] : (item[1], str(curLocation)+'/'+str(file))}
                finalRes.append(newItem)
            else:
                finalRes.remove(checkExistence)
                oldValue = checkExistence[item[0]]
                curLocation = path[path.rfind(rootDirectory):]
                if not str(curLocation)+'/'+str(file) in oldValue[1]:
                    newValue = (item[1], oldValue[1] + ','+ str(curLocation)+'/'+str(file))
                else:
                    newValue = (item[1], oldValue[1])
                     
                newItem = { item[0] : newValue}
                finalRes.append(newItem)
    return finalRes

MAX_MESSAGE_LENGTH = 16384

class RemoteClient(asyncore.dispatcher):

    """Wraps a remote client socket."""

    def __init__(self, host, socket, address):
        asyncore.dispatcher.__init__(self, socket)
        self.host = host
        self.outbox = collections.deque()
        self.address = address

    def say(self, message):
        self.outbox.append(message)

    def handle_read(self):
        client_message = self.recv(MAX_MESSAGE_LENGTH)        
        self.host.handle_read(client_message, self.address)

    def handle_write(self):
        if not self.outbox:
            return
        message = self.outbox.popleft()
        if len(message) > MAX_MESSAGE_LENGTH:
            raise ValueError('Message too long')
        self.send(message)

class Host(asyncore.dispatcher):
    def __init__(self, address=('localhost', 10003)):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(address)
        self.listen(1)
        log_to_file("Listening...")
        self.remote_clients = [] # list of clients connected
        self.validationRunning = [] #list of dictionary ID's for which validation is running
        self.buffer_requests_list = [] # list of clients to which request for buffer was sent
    
    #Method to remove client once the connection has been closed
    def remove_from_clients(self, client_address):
        global openBuffers
        for remote_client in self.remote_clients:
            if remote_client.address == client_address:
                log_to_file('Removing client: '+str(remote_client)+' from open clients list: '+str(self.remote_clients))
                self.remote_clients.remove(remote_client)                
                log_to_file('Open connections after removal: '+str(self.remote_clients))
                if not self.remote_clients:
                    log_to_file('Clearing buffers...')
                    openBuffers.clear()
                    log_to_file('Clearing clientInitPath...')
                    clientInitPath.clear()
        
    def handle_accept(self):
        global testingList
        socket, addr = self.accept() # For the remote client.
        log_to_file('Accepted client at '+ str(addr))
        self.remote_clients.append(RemoteClient(self, socket, addr))

    def handle_read(self, client_request, client_address):
        try:
            log_to_file('----------------------------')
            
            #If there's close connection request
            if client_request is None or client_request == b'':
                log_to_file('End of connection: '+str(client_address))
                self.remove_from_clients(client_address)
                return
            
            #print("REQUEST: "+str(client_request))
            requestDecoded = json.loads(client_request.decode("utf-8"))
            
            #Get PID number and tab page number to use them as identifiers for buffer dictionary
            log_to_file("RequestType: "+ str(requestDecoded['type']) +", PID incoming: "+str(requestDecoded['pid'])+", tab_page_number: "+str(requestDecoded['tab_page_number']))
            dictionaryID = str(requestDecoded['pid']) + "_" + str(requestDecoded['tab_page_number'])
            
            if requestDecoded['type'] == "sendCurrentWorkingDirectory":
                log_to_file("Current working directory request received...")
                # Fork new process which will calculate project info
                if 'root_filename' in requestDecoded.keys():
                    root_filename = requestDecoded['root_filename']
                    print("FILENAME GIVEN: "+str(root_filename))
                else: #default for python
                    root_filename = '__init__.py'
                t = threading.Thread(target=get_all_definitions_at_init, args=(clientInitPath, dictOfFuncsAndClasses, clientRootFileName, requestDecoded['current_working_dir'], dictionaryID, root_filename))
                t.daemon = True
                t.start()
                return
                
            elif (requestDecoded['type'] == "sendWholeFile"):
                log_to_file("Whole buffer received...")
                buffer = string_to_buffer(requestDecoded['whole_file'])
                tempBuffer = {dictionaryID : buffer}
                openBuffers.update(tempBuffer)
                return
            
            #Rest of the requests are ID dependant
            
            #No such an ID found (something is wrong) - send request for buffer to the client
            if not dictionaryID in openBuffers.keys():
                if not dictionaryID in self.buffer_requests_list:
                    print("NO SUCH AN ID, request sent")
                    request = json.dumps({'type_of_request' : 'requestForBuffer'})
                    self.respond(bytes(request, "UTF-8"), client_address)
                    self.buffer_requests_list.append(dictionaryID)
            else:    
                if (requestDecoded['type'] == "parseAndValidate"):
                    log_to_file("Parse and validate request...")
                    if not self.validationRunning:                    
                            self.validationRunning = True
                            #t2 = threading.Thread(target=parse_and_validate,args=(self, openBuffers[dictionaryID], client_address))
                            t2 = threading.Thread(target=parse_and_validate,args=(self, dictionaryID, client_address, requestDecoded['number_of_iterations']))
                            t2.daemon = True
                            t2.start()
                        #else:
                            #log_to_file('No such an ID')
                    else:
                        log_to_file("Can not validate at this moment, validation already running...")
                    
                elif (requestDecoded['type'] == "getAutocomplete"):
                    log_to_file("Auto complete request...")
                    t3 = threading.Thread(target = get_auto_completion, args=(self, client_address, openBuffers[dictionaryID], requestDecoded['variable'], requestDecoded['line_number']))
                    t3.daemon = True
                    t3.start()
                
                elif (requestDecoded['type'] == "getAllDefinitions"):
                    log_to_file("Get all definitions request...")
                    #if dictionaryID in clientInitPath:
                    #    if clientInitPath[dictionaryID] in dictOfFuncsAndClasses:
                    t4 = threading.Thread(target = respond_definitions, args=(self, client_address, dictionaryID, requestDecoded['current_directory'], requestDecoded['filename']))
                    t4.daemon = True
                    t4.start()
                
                elif (requestDecoded['type'] == "updateLine"):
                    #log_to_file("Update line request...")
                    buffer = openBuffers[dictionaryID]
                    lengthOfBuffer = len(buffer)
                    numberOfIncomingLines = int(requestDecoded['number_of_lines'])
                    
                    if lengthOfBuffer == numberOfIncomingLines:
                        if 'previousline_text' in requestDecoded.keys():
                            buffer[int(requestDecoded['line_number']) - 2] = requestDecoded['previousline_text']
                            
                        if 'nextline_text' in requestDecoded.keys():
                            buffer[int(requestDecoded['line_number'])] = requestDecoded['nextline_text']
                            
                        buffer[int(requestDecoded['line_number']) - 1] = requestDecoded['line_text']
                        
                    elif lengthOfBuffer < numberOfIncomingLines:
                        buffer.insert(int(requestDecoded['line_number']) - 1, requestDecoded['line_text'])
                        if 'previousline_text' in requestDecoded.keys():
                            buffer[int(requestDecoded['line_number']) - 2] = requestDecoded['previousline_text']
                            
                        if 'nextline_text' in requestDecoded.keys():
                            buffer[int(requestDecoded['line_number'])] = requestDecoded['nextline_text']
                            
                    elif lengthOfBuffer > numberOfIncomingLines:
                        del buffer[int(requestDecoded['line_number']) - 1]
                    
                    tempBuffer = {dictionaryID : buffer}
                    openBuffers.update(tempBuffer) 
                    #log_to_file("CURRENT BUFFER:"+ str(openBuffers) +"\n" + buffer_to_string(openBuffers[dictionaryID]))
            log_to_file('----------------------------')

        except Exception as msg:
            traceback.print_exc()
            log_to_file("Error: "+str(msg))
    
    def respond(self, message, client_address):
        #log_to_file('Responding to client: ' + str(client_address) +"\nMessage: "+ str(message))
        for remote_client in self.remote_clients:
            if remote_client.address == client_address:
                remote_client.say(message)

if __name__ == "__main__":
    try:
        #set higher recursion limit
        sys.setrecursionlimit(10000)
        
        log_to_file("-----------------------------------")
        log_to_file("Server started")
        
        # holds information about buffers per given pid+tab_page_number
        openBuffers = dict()
        
        #holds info about __init__ file locations and corresponding dictionaries with
        #all classdefs and funcdefs in all given files
        dictOfFuncsAndClasses = dict()
        
        # at last, hold info which PID + tab page number is located on which init path
        # (if any is found)
        clientInitPath = dict()
        
        # hols information about name of root file (sent from plugin)
        clientRootFileName = dict()
        
        #Create host
        port = 10003 #default value
        args = sys.argv
        if len(args) == 2:
            port = args[1]
        log_to_file('Creating host on localhost, port no. '+str(port))  
        
        host = Host(address=('localhost', int(port)))
        
        #Creeate handler which will repeat itself and recalculate project definitions
        tDefs = threading.Thread(target=recalculate_definitions, args=(dictOfFuncsAndClasses,clientInitPath))
        tDefs.daemon = True
        tDefs.start()
        
        log_to_file('Waiting for connection...')
        
        #Loop forever waiting for new clients
        asyncore.loop()
        
    except Exception as error:
        log_to_file(str(error))
        log_to_file("-----------------------------------")
