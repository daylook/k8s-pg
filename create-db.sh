#!/bin/bash

# Get superuser password
PGPASSWORD=$(kubectl get secret ha-postgres-superuser -o jsonpath='{.data.password}' | base64 --decode)
echo $PGPASSWORD   # save it or export PGPASSWORD=$PGPASSWORD

# Create table (one-time)
PRIMARY=$(kubectl get cluster ha-postgres -o jsonpath='{.status.currentPrimary}')
kubectl port-forward pod/$PRIMARY 5432:5432 &   # keep this running in background
sleep 2
psql -h 127.0.0.1 -U postgres -d postgres -c "
  CREATE TABLE IF NOT EXISTS traffic_log (
    id SERIAL PRIMARY KEY,
    ts TIMESTAMPTZ DEFAULT NOW()
  );
"
# Kill the port-forward or leave it running
