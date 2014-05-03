""""
"
" Vimscript plugin combined with python for providing type inference and code completion options.
"
" Written by L.Zak as Diploma thesis.
"
""""

let s:current_file=expand("<sfile>:r")
let s:current_path = resolve(expand('<sfile>:p'))
let s:script_path = s:current_file . '.py'
let currenttab_page_number = tabpagenr()

python << EOF
import vim

if sys.version_info[:2] < (2, 5):
	raise AssertionError('Vim must be compiled with Python 2.5 or higher; you have ' + sys.version)
EOF

" ROOT FILENAME 
if exists("g:Pynfer_default_python_settings")
    let root_filename = g:Pynfer_default_python_settings
else
    let root_filename = 0
endif

if root_filename > 0
	:set number
	:set showmode
	:set tabstop=4
endif

:set completeopt=menuone,longest,preview
:set backspace=indent,eol,start
syntax on

python << PYEND
import os
import inspect
import socket
import sys
import vim
import traceback
import asyncore
import collections
import select
import time
import threading
import json

#Dummy value
client = None

#Validation running flag (similar to the daemon one)
validation_running = False

# Current process ID
pid = os.getpid()

# Increased recursion limit
sys.setrecursionlimit(10000)

# Value indicating whether the connection was successful
connected = False

# Current buffer
buffer = []

# How often should check for open socket for read/write plus upper bound on time after gives up
timeFract = 0.01
timeLimit = 20

def canRead(serverSocket):
    availability = select.select(serverSocket, serverSocket, serverSocket)
    receiveTimeout = 0
    while not availability[0]:
        time.sleep(timeFract)
        availability = select.select(serverSocket, serverSocket, serverSocket)
        receiveTimeout += timeFract
        if receiveTimeout >= timeLimit:
            raise Exception("Timeout on read occurred.")
    return True

def canWrite(serverSocket):
    receiveTimeout = 0
    availability = select.select(serverSocket, serverSocket, serverSocket)
    while not availability[1]:
        time.sleep(timeFract)
        availability = select.select(serverSocket, serverSocket, serverSocket)
        receiveTimeout += timeFract
        if receiveTimeout >= timeLimit:
            raise Exception("Timeout on write occurred.")
    return True

def incomingStringToBuffer(incomingString):
    return incomingString.splitlines()

MAX_MESSAGE_LENGTH = 16384

class Client(asyncore.dispatcher):
    def __init__(self, host_address, name):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.name = name
#        print('Connecting to host at %s', host_address)
        self.connect(host_address)
        self.outbox = collections.deque()

    def send_message(self, message):
        self.outbox.append(message)
	
	def handle_write(self):
		if not self.outbox:
			return None

        message = self.outbox.popleft()

        serverSocket = [self.socket]
        if canWrite(serverSocket):
            self.send(message)

    def handle_read(self):
        serverSocket = [self.socket]
        if canRead(serverSocket):
            message = self.recv(MAX_MESSAGE_LENGTH)
            return message
        else:
            return False

def vim_quote(s):
    return s.replace("'", "''")

def parseAndValidateCall(iterations):
    global validation_running

    if not validation_running:
        try:
            validation_running = True
            #Initialize the request and fill in request type.
            tab_page_number = vim.eval("currenttab_page_number")
#            request = RequestToServer("parseAndValidate", pid, tab_page_number)
            request_parse = json.dumps({'type' : 'parseAndValidate', 'pid' : pid, 'tab_page_number' : tab_page_number, 'number_of_iterations' : iterations})
            
            client.send_message(request_parse)
            vim.command(':call ErrorClear()')
            
            data = client.handle_read()
            response = json.loads(data)

            #Check if daemon did not send "I have nothing to do with this, unknown buffer" response
            if "type_of_request" in response.keys() and response['type_of_request'] == 'requestForBuffer':
                vim.command("call SendWholeBuffer()")
                print("Pynfer: Synchronizing buffer with the daemon...")
                time.sleep(1)
                validation_running = False
                print("Pynfer: Synchronizing buffer with the daemon... Done")
            else:    
                #Indentation error came - show error
                if 'message' in response.keys() and 'line_number' in response.keys():
                    vim.command(':call ErrorHighlight({0},{1})'.format(response['line_number'], 2))
                    vim.command("let qf_item = {}")
                    vim.command("let qf_item.bufnr = bufnr('%')")
                    vim.command("let qf_item.filename = expand('%')")
                    vim.command("let qf_item.lnum = %s" % str(response['line_number']))
                    vim.command("let qf_item.text = '%s'" % vim_quote(response['message']))
                    vim.command("let qf_item.type = 'E'")
                    vim.command("call add(b:qf_list, qf_item)")
                else:
                    if 'problems' in response.keys():
                        for problem in response['problems']:
                            vim.command(':call ErrorHighlight({0},{1})'.format(problem[0], 2))
                            vim.command("let qf_item = {}")
                            vim.command("let qf_item.bufnr = bufnr('%')")
                            vim.command("let qf_item.filename = expand('%')")
                            vim.command("let qf_item.lnum = %s" % str(problem[0]))
                            vim.command("let qf_item.text = '%s'" % vim_quote(problem[1]))
                            vim.command("let qf_item.type = 'E'")
                            vim.command("call add(b:qf_list, qf_item)")

                    if 'warnings' in response.keys():
                        for warning in response['warnings']:
                            vim.command(':call WarningHighlight({0},{1})'.format(warning[0], 2))
                            vim.command("let qf_item = {}")
                            vim.command("let qf_item.bufnr = bufnr('%')")
                            vim.command("let qf_item.filename = expand('%')")
                            vim.command("let qf_item.lnum = %s" % str(warning[0]))
                            vim.command("let qf_item.text = '%s'" % vim_quote(warning[1]))
                            vim.command("let qf_item.type = 'W'")
                            vim.command("call add(b:qf_list, qf_item)")

                vim.command("call setqflist(b:qf_list, '')")
                vim.command("let quickfix_count = GetQuickFixStackCount()")
                vim.command("call ActivateQuickFixWindow(quickfix_count)")
                validation_running = False
        except Exception, msg:
            print("Pynfer: Error in ParseAndValidate: ", msg)
            validation_running = False

PYEND

function! StartupFunction()

let currenttab_page_number = tabpagenr()

" ROOT FILENAME 
if exists("g:Pynfer_root_filename")
    let root_filename = g:Pynfer_root_filename
else
    let root_filename = 0
endif

" PORT
if exists("g:Pynfer_port_number")
    let port_number = g:Pynfer_port_number
else
    let port_number = 0
endif

python << PYEND

#startup function
try:
    #check for .vimrc port number and set default one if it is not present
    port_number = int(vim.eval("port_number"))

    if port_number == 0: #default value
        port_number = 10003

    server_address = ('localhost', port_number)
    client = Client(server_address, 'Client')
    tab_page_number = vim.eval("currenttab_page_number")
    connected = True

    #check settings for root filename
    root_file = vim.eval('root_filename')
    if root_file != '0':
        temp_dict = {'root_filename' : root_file}
    else:
        temp_dict = None
    # send path of file so server can try to reach __init__ and get all funcdefs and classdefs
    cur_directory = os.getcwd()
    
    startup_dict = {'type' : 'sendCurrentWorkingDirectory', 'pid' : pid, 'tab_page_number' : tab_page_number, 'current_working_dir' : cur_directory}
    if temp_dict:
        startup_dict.update(temp_dict)

    request = json.dumps(startup_dict)
    client.send_message(request)

    # replace auto commands with setting it here - avoid having too many auto commands down there
    vim.command("set omnifunc=GetOmnicomplete")
    vim.command("set completefunc=GetFuncAndClassDefs")
    vim.command("call SendWholeBuffer()")    
    
except Exception as error: 
    print("Pynfer: Could not connect to the remote server: "+ str(error))
    client = None
	

PYEND
endfunction


" -------------------- SEND WHOLE BUFFER ----------------------------
function! SendWholeBuffer()
	let currenttab_page_number = tabpagenr()

    "Get all lines in current buffer as list
    let lines = getbufline(bufnr("%"), 1, "$")
	let i = 0
	let result = ""
	while i < len(lines)
		let curLine = lines[i]
		let result = result . curLine . "\n"
		let i += 1
	endwhile

	
python << PYTHONEND2

if client:
    try:
        tab_page_number = vim.eval("currenttab_page_number")
        result = vim.eval("result")
        buffer = incomingStringToBuffer(result)
        request_whole = json.dumps({'type' : 'sendWholeFile', 'pid' : pid, 'tab_page_number' : tab_page_number, 'whole_file' : result})

        # Send data
        client.send_message(request_whole)
        
    except Exception, msg:
	    print("Pynfer: Error in SendWholeBuffer: ", msg)
PYTHONEND2
endfunction


" ------------------SEND CURRENT LINE-------------------------------
function! SendCurrentLine()
	let currenttab_page_number = tabpagenr()

	let charNumber = getpos(".")
	let curLine = getline(".")
	let curLineNumber = line(".")
	let numberOfLines = line("w$")

	let previousLine = getline(curLineNumber - 1)
	let nextLine = getline(curLineNumber + 1)

python << PYTHONEND
if client:
    # Whole function is in try except block so it stops after 2 seconds = server does not respond
    currentChar = vim.eval("charNumber")

    #Get python variables from vim variables.
    line_number = int(vim.eval("curLineNumber"))
    line_text = vim.eval("curLine")
    number_of_lines = int(vim.eval("numberOfLines"))

    nextLine = vim.eval("nextLine")
    previousLine = vim.eval("previousLine")

    tab_page_number = vim.eval("currenttab_page_number")

    if  number_of_lines != len(buffer) or buffer[int(line_number) - 1] != line_text:
        json_dict = {'type' : 'updateLine', 'pid' : pid, 'tab_page_number' : tab_page_number, 'number_of_lines' : number_of_lines, 'line_number' : line_number, 'line_text' : line_text}

        #Add previous line and next line to the request.
        if line_number - 1 >= 1:
            temp = {'previousline_text' : previousLine}
            json_dict.update(temp)

        if line_number + 1 <= number_of_lines:
            temp = {'nextline_text' : nextLine}
            json_dict.update(temp)

        request = json.dumps(json_dict)

	    #Send data via port.
        client.send_message(request)

        #Update local buffer also.
        lengthOfBuffer = len(buffer)
        difference = number_of_lines - lengthOfBuffer

        if difference < 0:
            difference = difference * -1;

        #Something horrible happened - send whole buffer.
        if difference > 1:
            vim.command(':call SendWholeBuffer()')
        elif lengthOfBuffer == number_of_lines:
            buffer[int(line_number) - 1] = line_text
        elif lengthOfBuffer < number_of_lines:
            buffer.insert(int(line_number) - 1, line_text)
        elif lengthOfBuffer > number_of_lines:
            del buffer[int(line_number) - 1]
PYTHONEND
endfunction 


" ------------------PARSE AND VALIDATE-------------------------------
function! ParseAndValidate()
	let currenttab_page_number = tabpagenr()

	let b:matched = []
    let b:matchedlines = {}

    let b:qf_list = []
    let b:qf_window_count = -1	
    
    let popup_visible = pumvisible()

    if exists("g:Pynfer_number_of_iterations")
        let number_of_iterations = g:Pynfer_number_of_iterations
    else
        let number_of_iterations = 10
    endif

python << PYTHONEND

popup_visible = vim.eval("popup_visible")

if client and not validation_running:
    iterations = int(vim.eval("number_of_iterations"))
    t = threading.Thread(target=parseAndValidateCall, args=(iterations,))
    t.daemon = True
    t.start()
PYTHONEND

    " Uncomment next line to show errors automatically. TODO: input parameter from vimrc.
	" cope displays quickfix window.
	"cope
endfunction



" ------------------OMNI COMPLETITION-------------------------------


fun! GetOmnicomplete(findstart, base)
  let g:option = ""
  let b:return_list = []

  let charNumber = getpos(".")
  let curLine = getline(".")	
  let curLineNumber = line(".")

  if a:findstart
    " locate the start of the word
    let line = getline('.')
    let start = col('.') - 1
    while start > 0 && line[start - 1] =~ '\a'
      let start -= 1
    endwhile
    return start
  else
	python << ENDOFPYTHONOMNI
if client:
    try:
        currentChar = vim.eval("charNumber")
        line_text = vim.eval("curLine")
        line_text_until_cursor = line_text[:int(currentChar[2]) - 1]
        line_number = int(vim.eval("curLineNumber"))

        request = json.dumps({'type' : 'getAutocomplete', 'pid' : pid, 'tab_page_number' : tab_page_number, 'variable' : line_text_until_cursor, 'line_number' : line_number})

        client.send_message(request)
        data = client.handle_read()

        omniRespond = json.loads(data)
        if "type_of_request" in omniRespond.keys() and omniRespond['type_of_request'] == 'requestForBuffer':
            print("Pynfer: Synchronizing buffer with the daemon...")
            vim.command("call SendWholeBuffer()")
            time.sleep(1)
            print("Pynfer: Synchronizing buffer with the daemon... Done. Please try again.")
        else:
            if 'options' in omniRespond.keys():
                for omniOption in omniRespond['options']:
                    word = omniOption[0]
                    info = ''
                    if len(omniOption) == 2:
                        info = omniOption[1]
                    # Info not working properly, disabled for now.
                    #vim.command("let option = {'word' : '%s', 'info' : '%s'}" %(vim_quote(word),vim_quote(info)))
                    vim.command("let option = {'word' : '%s'}" %(vim_quote(word)))
                    vim.command("call add(b:return_list, option)")

    except Exception, msg:
	    print("Pynfer: Error in OmniCompletition: ", msg)
ENDOFPYTHONOMNI
	
    return b:return_list
  endif
endfun


" ------------------ All functions and class defs ------------------

fun! GetFuncAndClassDefs(findstart, base)
  let file_path = expand('%:p')
  let filename = expand('%:t')
  let b:return_listFunc = []

  let charNumber = getpos(".")
  let curLine = getline(".")	
  let curLineNumber = line(".")

  if a:findstart
    " locate the start of the word
    let line = getline('.')
    let start = col('.') - 1
    return start
  else
python << ENDOFPYTHONGETDEFS

if client:
    try:
        currentChar = vim.eval("charNumber")
        line_text = vim.eval("curLine")
        line_text_until_cursor = line_text[:int(currentChar[2]) - 1]
        line_number = int(vim.eval("curLineNumber"))

        current_directory = os.getcwd()
        filename = vim.eval('filename')

        # Send message
        request = json.dumps({'type' : 'getAllDefinitions', 'pid' : pid, 'tab_page_number' : tab_page_number, 'current_directory' : current_directory, 'filename' : filename})
        client.send_message(request)

        # Get response
        data = client.handle_read()
        funcRespond = json.loads(data)
        if "type_of_request" in funcRespond.keys() and funcRespond['type_of_request'] == 'requestForBuffer':
            print("Pynfer: Synchronizing buffer with the daemon...")
            vim.command("call SendWholeBuffer()")
            time.sleep(1)
            print("Pynfer: Synchronizing buffer with the daemon...Done. Please, try user completion again.")
        else:
            if 'options' in funcRespond.keys():
                for funcOption in funcRespond['options']:
                    for key in funcOption.keys():
                        word = key
                        kind = funcOption[key][0]
                        menu = funcOption[key][1]
                        vim.command("let option = {'word' : '%s','menu' : '%s', 'kind' : '%s'}" %(vim_quote(word),vim_quote(menu),vim_quote(kind)))
                        vim.command("call add(b:return_listFunc, option)")

    except Exception, msg:
        traceback.print_exc()
        print("Pynfer: Error in GetAllDefs: ", msg)

ENDOFPYTHONGETDEFS
	
    return b:return_listFunc
  endif
endfun


" --------------------- AUTO COMPLETE REMAP -------------------- 

inoremap <expr> . MayComplete()
inoremap <expr> <Nul> MayCompleteNoDot()

func MayComplete()
return ".\<C-X>\<C-O>"
endfunc

func MayCompleteNoDot()
return "\<C-X>\<C-U>"
endfunc

"------------------ QUICK FIX WINDOW -----------------------------

" These functions were copied and modified for our purpose from PyFlakes tool.
" http://www.vim.org/scripts/script.php?script_id=2441
" All credits to: Kevin Watters.
 
function ActivateQuickFixWindow(...)
    try
        silent colder 9 " go to the bottom of quickfix stack
    catch /E380:/
    endtry

"    if s:quickfix_count > 0
    if a:1 > 0
        try
            exe "silent cnewer " . a:1
        catch /E381:/
            echoerr "Could not activate Quickfix Window."
        endtry
    endif
endfunction

function GetQuickFixStackCount()
    let l:stack_count = 0
    try
        silent colder 9
    catch /E380:/
    endtry

    try
        for i in range(9)
            silent cnewer
            let l:stack_count = l:stack_count + 1
        endfor
    catch /E381:/
        return l:stack_count
    endtry
endfunction

" ---------------------- Function called on VIM exit ------------------------
function! ExitFunction()
python client.close()
endfunction

" ---------------------- Highlighting functions -------------------

" Highlight errors via setting signs
function! ErrorHighlight(...)
	sign define piet text=! texthl=SpellBad
	exe ":sign place ".a:2." line=".a:1." name=piet file=" . expand("%:p") 
	highlight SignColumn ctermbg=black
endfunction

" Highlight warnings via setting signs
function! WarningHighlight(...)
	sign define warn text=! texthl=Search
	exe ":sign place ".a:2." line=".a:1." name=warn file=" . expand("%:p") 
	highlight SignColumn ctermbg=black
endfunction

" Clean error/warning signs marked by previous functions
function! ErrorClear()
	sign unplace *
endfunction

" --------------------- Settings --------------------------

" How often should program revalidate input - in miliseconds.
set updatetime=2000

augroup PythonCodeCheckerTest
    autocmd!
	autocmd VimEnter 	    *.py	:call StartupFunction() "On enter
	autocmd VimLeavePre	    *.py	:call ExitFunction() "On exit
	autocmd BufWritePost	*.py	:call SendWholeBuffer() "Triggerred right after saving buffer
"Holding cursor still in any mode:
	autocmd CursorHoldI 	*.py	:call ParseAndValidate()
	autocmd CursorHold 		*.py	:call ParseAndValidate()
"New buff : 
	autocmd BufAdd			*.py	:call SendWholeBuffer()
    autocmd BufAdd          *.py    :call ErrorClear()
"Switching between tabs:
    autocmd TabEnter        *.py    :call ErrorClear()
"Moving cursor around:
	autocmd CursorMoved		*py		:call SendCurrentLine()
	autocmd CursorMovedI		*py		:call SendCurrentLine()
augroup END
