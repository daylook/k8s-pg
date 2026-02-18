# k8s-pg
Scalable PostgreSQL database on Kubernetes Cluster

## How create the K8s cluster

```sh
# make sure you are in the k8s directory
cd k8s

# create the kind k8s cluster
kind create cluster --config kind-config.yaml --name ha-pg
kubectl cluster-info --context kind-ha-pg
```

## Scalable database solution

The [CNCF CloudNativePG (CNPG)](https://github.com/cloudnative-pg/cloudnative-pg) provides automatic failover/switchover with zero data loss on graceful events, built-in PodDisruptionBudget protection, and a stable read-write service that always points to the current primary. We find its documentation at: [CloudNativePG](https://cloudnative-pg.io/docs/1.28/)

Other options: 
- [Zalando Postgres Operator](https://github.com/zalando/postgres-operator)
- [Crunchy Data Postgres Operator](https://github.com/CrunchyData/postgres-operator)

Install the operator on the cluster
```sh
kubectl apply --server-side -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.27/releases/cnpg-1.27.3.yaml
kubectl wait --for=condition=Available deployment/cnpg-controller-manager -n cnpg-system --timeout=120s
```

After the operator is finally provisioned, deploy the HA postgres replicas with:
```sh
# make sure you are in the k8s directory
cd k8s
# apply the HA cluster
kubectl apply -f ha-postgres.yaml

# wait for all 3 pods Running and Ready
kubectl wait --for=condition=Ready cluster/ha-postgres --timeout=5m

# after succeeding the previous command
kubectl get cluster ha-postgres -o wide
kubectl get pods -l cnpg.io/cluster=ha-postgres -o wide

# to verify the services
kubectl get svc -l cnpg.io/cluster=ha-postgres
```

To run the traffic generator test:

### Step 1 — One-time table setup

To create the `traffic_log` table:

```sh
./create-db.sh
```

> **Note:** After successfully table creation, the port-forward will print a `connection reset by peer` harmless error after psql disconnects — this is a kubectl bug on macOS/arm64. 

### Step 2 — Test the traffic switch

Open several terminals:

**Terminal 1** — keep the port-forward tunnel open:
```sh
export PGPASSWORD=$(kubectl get secret ha-postgres-superuser -o jsonpath='{.data.password}' | base64 --decode)
PRIMARY=$(kubectl get cluster ha-postgres -o jsonpath='{.status.currentPrimary}')
echo "Forwarding to primary pod: $PRIMARY"

# Forward to the pod/$PRIMARY
# Forwarding to the service svc/ha-postgres-rw crashes with "connection reset by peer" on macOS/arm64
kubectl port-forward pod/$PRIMARY 5432:5432
```

**Terminal 2** — run the traffic generator script:
```sh
# Activate the venv (create it first if needed)
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary

# Export the password so the script picks it up automatically
export PGPASSWORD=$(kubectl get secret ha-postgres-superuser -o jsonpath='{.data.password}' | base64 --decode)

python3 ./traffic-generator.py
```

**Terminal 3** - Trigger the Disruption

Identify the node hosting the current primary and perform the voluntary node drain
```sh
./drain-node.sh
```

**Terminal 4** - Prove Recovery
While the traffic generator is still running, open another terminal and watch:
```sh
watch -n 1 'kubectl get pods -l cnpg.io/cluster=ha-postgres -o wide && echo "Current primary:" && kubectl get cluster ha-postgres -o jsonpath="{.status.currentPrimary}"'
```

You will see:
- One pod terminate and a new one become Ready.
- The currentPrimary value changes to a different pod.
- The traffic-generator output continues with ✅ Write succeeded after at most a few transient errors.

**Terminal 5** - Finally, verify zero data loss and continuity
```sh
# Stop port-forward if needed, then re-start one
kubectl port-forward svc/ha-postgres-rw 5432:5432 &
sleep 2
psql -h localhost -U postgres -d postgres -c "SELECT COUNT(*) FROM traffic_log;"
```
The row count keeps increasing across the entire test with no gaps in the timestamps around the drain moment.




## Cluster Cleanup
```sh
# deactivate the python env
# make sure you are in the root
deactivate

# delete the kind cluster
kind delete cluster --name ha-pg
```