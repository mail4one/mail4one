#!/bin/sh

# kill "$(cat current.pid)"

# echo "starting python server"

python3 -m http.server

# echo $! > current.pid

# echo "started python server"
