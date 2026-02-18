#!/bin/bash

# show the running node and the primary pod
PRIMARY_POD=$(kubectl get cluster ha-postgres -o jsonpath='{.status.currentPrimary}')
NODE=$(kubectl get pod $PRIMARY_POD -o jsonpath='{.spec.nodeName}')
echo "Primary pod: $PRIMARY_POD is on node: $NODE"

sleep 2

# drain the node
echo "Draining node: $NODE"

kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data --force