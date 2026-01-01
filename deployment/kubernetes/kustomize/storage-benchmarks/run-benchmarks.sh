#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="${NAMESPACE:-default}"

echo "========================================="
echo "Storage Benchmark Runner"
echo "========================================="
echo ""

# Function to wait for job completion
wait_for_job() {
    local job_name=$1
    local timeout=600  # 10 minutes timeout
    local elapsed=0

    echo "Waiting for job $job_name to complete..."
    while [ $elapsed -lt $timeout ]; do
        status=$(kubectl get job $job_name -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null || echo "")
        failed=$(kubectl get job $job_name -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null || echo "")

        if [ "$status" == "True" ]; then
            echo "✓ Job $job_name completed successfully"
            return 0
        elif [ "$failed" == "True" ]; then
            echo "✗ Job $job_name failed"
            return 1
        fi

        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done

    echo ""
    echo "✗ Job $job_name timed out"
    return 1
}

# Function to get job logs
get_job_logs() {
    local job_name=$1
    local pod_name=$(kubectl get pods -n $NAMESPACE -l job-name=$job_name -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

    if [ -n "$pod_name" ]; then
        kubectl logs -n $NAMESPACE $pod_name
    else
        echo "No pod found for job $job_name"
    fi
}

# Cleanup function
cleanup() {
    local job_name=$1
    local pvc_name=$2

    echo "Cleaning up $job_name..."
    kubectl delete job $job_name -n $NAMESPACE --ignore-not-found=true
    kubectl delete pvc $pvc_name -n $NAMESPACE --ignore-not-found=true
}

# Parse arguments
STORAGE_TYPE="${1:-both}"

echo "Storage type to benchmark: $STORAGE_TYPE"
echo ""

# Run iSCSI benchmark
if [ "$STORAGE_TYPE" == "iscsi" ] || [ "$STORAGE_TYPE" == "both" ]; then
    echo "========================================="
    echo "Running iSCSI Benchmark"
    echo "========================================="
    echo ""

    # Cleanup any existing resources
    cleanup "fio-iscsi-benchmark" "fio-iscsi-benchmark-pvc"
    sleep 2

    # Apply the benchmark
    kubectl apply -f "$SCRIPT_DIR/base/fio-iscsi-benchmark.yml"

    # Wait for job to complete
    if wait_for_job "fio-iscsi-benchmark"; then
        echo ""
        echo "========================================="
        echo "iSCSI Benchmark Results"
        echo "========================================="
        get_job_logs "fio-iscsi-benchmark"
        echo ""
    fi

    # Optional: cleanup immediately or leave for manual inspection
    # Uncomment the line below to auto-cleanup
    # cleanup "fio-iscsi-benchmark" "fio-iscsi-benchmark-pvc"
fi

echo ""

# Run NFS benchmark
if [ "$STORAGE_TYPE" == "nfs" ] || [ "$STORAGE_TYPE" == "both" ]; then
    echo "========================================="
    echo "Running NFS Benchmark"
    echo "========================================="
    echo ""

    # Cleanup any existing resources
    cleanup "fio-nfs-benchmark" "fio-nfs-benchmark-pvc"
    sleep 2

    # Apply the benchmark
    kubectl apply -f "$SCRIPT_DIR/base/fio-nfs-benchmark.yml"

    # Wait for job to complete
    if wait_for_job "fio-nfs-benchmark"; then
        echo ""
        echo "========================================="
        echo "NFS Benchmark Results"
        echo "========================================="
        get_job_logs "fio-nfs-benchmark"
        echo ""
    fi

    # Optional: cleanup immediately or leave for manual inspection
    # Uncomment the line below to auto-cleanup
    # cleanup "fio-nfs-benchmark" "fio-nfs-benchmark-pvc"
fi

echo ""
echo "========================================="
echo "Benchmark Summary"
echo "========================================="
echo ""
echo "To view logs again later, run:"
echo "  kubectl logs -n $NAMESPACE -l storage-type=iscsi"
echo "  kubectl logs -n $NAMESPACE -l storage-type=nfs"
echo ""
echo "To cleanup resources, run:"
echo "  kubectl delete -f $SCRIPT_DIR/base/"
echo ""
