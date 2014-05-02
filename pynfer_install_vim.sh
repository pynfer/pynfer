INSTALLPATH=$1
sudo mv tool/ $1
mkdir ~/.vim/plugin
cp plugins/pynfer.vim ~/.vim/plugin
chmod +x $1/daemon_start.sh
sudo ln -s $1/daemon_start.sh /usr/bin/pynfer
