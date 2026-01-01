# Storage Benchmarks

This directory contains IO benchmarks for testing storage performance in the Kubernetes cluster using `fio` (Flexible IO Tester).

## Storage Classes Tested

- **freenas-iscsi-csi**: iSCSI block storage
- **freenas-nfs-csi**: NFS file storage

## Benchmark Tests

Each storage class is tested with the following workloads:

1. **Random Read/Write (4K blocks)** - Mixed workload, 60s runtime, 4 jobs
2. **Sequential Read (1M blocks)** - Large sequential reads, 60s runtime
3. **Sequential Write (1M blocks)** - Large sequential writes, 60s runtime
4. **Random Read (4K blocks)** - High queue depth random reads, 60s runtime, 4 jobs
5. **Random Write (4K blocks)** - High queue depth random writes, 60s runtime, 4 jobs

## Quick Start

### Run Both Benchmarks

```bash
./run-benchmarks.sh both
```

### Run Individual Benchmarks

```bash
# iSCSI only
./run-benchmarks.sh iscsi

# NFS only
./run-benchmarks.sh nfs
```

### Manual Deployment

```bash
# Deploy benchmarks
kubectl apply -f base/

# Check job status
kubectl get jobs -n default -l app=fio-benchmark

# View logs
kubectl logs -n default -l storage-type=iscsi
kubectl logs -n default -l storage-type=nfs

# Cleanup
kubectl delete -f base/
```

## Understanding Results

The fio output includes key metrics:

- **IOPS**: Input/Output Operations Per Second
- **Bandwidth (BW)**: Throughput in MB/s or KB/s
- **Latency**: Average and percentile latencies (usec/msec)
- **slat**: Submission latency (time to submit IO)
- **clat**: Completion latency (time from submission to completion)
- **lat**: Total latency

### Typical Performance Expectations

**iSCSI (Block Storage):**
- Sequential Read/Write: 100-500 MB/s (depends on network and disk)
- Random 4K Read IOPS: 5,000-50,000 (depends on SSD/HDD)
- Random 4K Write IOPS: 5,000-50,000 (depends on SSD/HDD)

**NFS (File Storage):**
- Sequential Read/Write: 50-300 MB/s (typically lower than iSCSI)
- Random 4K Read IOPS: 1,000-10,000 (lower than iSCSI)
- Random 4K Write IOPS: 1,000-10,000 (lower than iSCSI)

## Cleanup

The benchmark jobs are configured with `ttlSecondsAfterFinished: 3600` (1 hour), so they will auto-cleanup after completion.

To manually cleanup:

```bash
kubectl delete job fio-iscsi-benchmark fio-nfs-benchmark -n default
kubectl delete pvc fio-iscsi-benchmark-pvc fio-nfs-benchmark-pvc -n default
```

## Customization

To modify the benchmark parameters, edit the job definitions in `base/`:

- **runtime**: Duration of each test (default: 60s)
- **size**: Size of test file (default: 2G)
- **bs**: Block size (4k or 1M)
- **iodepth**: IO queue depth (affects parallelism)
- **numjobs**: Number of parallel workers

## Notes

- Each benchmark creates a 10Gi PVC for testing
- Tests use direct IO (`--direct=1`) to bypass OS cache
- Results may vary based on cluster load, network conditions, and storage backend
- Run benchmarks during off-peak hours for most accurate results
