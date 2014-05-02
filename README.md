PYNFER
==============

Pynfer is a supportive tool for python development using symbolic execution approach to detect various errors for Python3 language.

NOTE: Current version does not support *import* keyword therefore the program can not be used to its full potential. We are working on resolving this final issue as soon as possible.

It is using client-service aproach and so far the client has been implemented for vim text editor. More solutions will be added in the future.

Installation
--------------

Make sure that both python3 (easily doable with running *python3* command in console) and vim text editor are installed. To check that try running *vim* command in console. If unknown command error is returned, install vim by running following: (Vim needs to be installed with python support).

		sudo apt-get install vim

- Download the solution.

- Extract the downloaded archive.

- Either run *pynfer_install_vim.sh* script (which will try to complete all of the steps automatically) by typing 

		sh pynfer_install_vim.sh \$1

	where *$1* is location, where pynfer should be installed (for example */opt/pynfer* ) or follow step-by-step guide provided in the following steps.



**Only follow these steps if *pynfer_install_vim.sh* was not successful.**

- Move extracted folder to somewhere more appropriate (for example */opt/* folder (Note: location of your downloads might be different):

		sudo mv ~/Downloads/pynfer-master/tool /opt/pynfer 

- Make sure that there exists directory in which vim checks for plugins. To create such a directory write 

		mkdir ~/.vim/plugin

- Copy *pynfer.vim* file to the directory created in the above step

		cp ~/Downloads/pynfer-master/plugins/pynfer.vim ~/.vim/plugin

- *Optional*: Add port number and number of iterations to local vim configuration file **vimrc** - usually located at *~/.vimrc*. There are default values specified, so this step is completely optional (see \ref{sec:vimrc} for details).

9. Run daemon.py at */opt/pynfer* directory:

		python3 /opt/pynfer/daemon.py

	To specify other than the default port to be used, add it as an integer argument following the command: 

		python3 /opt/pynfer/daemon.py *PortNumber*

- *Optional:* To avoid always navigating to the source folder where daemon.py is located and running above mentioned command, create symbolic link to shell script executing this command for you. First of all set executable permission on *daemon_start.sh* file located in */opt/pynfer* directory:

		chmod +x /opt/pynfer/daemon.sh

	After that create symbolic link to this script:

		sudo ln -s /opt/pynfer/daemon.sh /usr/bin/pynfer

	From now on, running

		pynfer

	in console starts our daemon service.

- Open any *.py file with vim and enjoy our tool !

		vim example.py

Note: Daemon gets closed on reboot or shut down of the computer, therefore before next usage it needs to be started again. Once our project will be completed our installation will add daemon to "run on system start" list and this step will be omitted.	
