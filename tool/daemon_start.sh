SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")
python3 $SCRIPTPATH/daemon.py $1
