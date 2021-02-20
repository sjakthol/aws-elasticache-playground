# aws-elasticache-playground

CloudFormation templates, scripts and notes for working with Amazon ElastiCache for Redis.

## Prerequisites

* VPC, subnet and bucket stacks from [sjakthol/aws-account-infra](https://github.com/sjakthol/aws-account-infra).

## Deployment

Deploy stacks as follows setup ElastiCache for Redis:

```bash
# Workspace Node
make deploy-ec2-workspace

# Redis cluster
make deploy-redis-cluster
```

Once done, you'll have

* an EC2 instance you can log into with SSM Session Manager
* a Redis cluster you can access from workspace instance.

## Working with Redis

### Setting up Workspace

You can install redis-cli from the Amazon Linux 2 Extras repository:

```
sudo amazon-linux-extras enable redis4.0
sudo yum install -y redis htop tmux
```

You can then use redis-cli to connect to your Redis cluster:

```
redis-cli -h <redis_address>
```

You can find the hostname from outputs of the Redis cluster stack.

### Generating Data

[scripts/generate_data.py](scripts/generate_data.py) generates random
data you can push to your Redis cluster. Use it as follows:

```
python3 generate_data.py 100000 | redis-cli -h <redis_address> --pipe
```

This commands generates 100,000 SET commands with random keys and values, and sends
those to Redis.

### Migration Testing

You can create two Redis clusters to test migration of data from one
cluster to another.

All benchmark results were obtained with a following setup:

* Source Redis: ElastiCache Redis v4.0.10 on r3.large node.
* Target Redis: ElastiCache Redis v6.x on r6g.large node.
* Migration Instance: c6g.2xlarge instance

All instances and Redis nodes are were in the same Availability Zone
of eu-west-1 region.

#### rump

https://github.com/stickermule/rump

rump is a tool for synchronizing two Redis clusters. It uses `SCAN`, `DUMP` and `RESTORE`
commands to synchronize keys between two Redis clusters.

You can use it as follows (check rump repository for latest version and documentation):

```
# Install (check rump repo for latest version and installation method)
curl -LO https://github.com/stickermule/rump/releases/download/1.0.0/rump-1.0.0-linux-arm
mv rump-1.0.0-linux-arm rump && chmod +x rump

# or this for x86
curl -LO https://github.com/stickermule/rump/releases/download/1.0.0/rump-1.0.0-linux-amd64
mv rump-1.0.0-linux-amd64 rump && chmod +x rump

# Migrate
./rump -silent -from redis://<something>.cache.amazonaws.com:6379 -to redis://<something_else>.cache.amazonaws.com:6379
```

Rump reached a rate of ~2200 keys / second in tests.

#### RIOT

https://github.com/redis-developer/riot
https://developer.redislabs.com/riot/riot-redis.html

RIOT provides means to synchronize exiting and modified keys data between two Redis
clusters.

You can use it as follows (check RIOT repository for latest version and documentation):

```
# Pre-requisites (java)
sudo yum install -y java-11-amazon-corretto-headless

# RIOT
curl -LO https://github.com/redis-developer/riot/releases/download/v2.5.2/riot-redis-2.5.2.zip
unzip -q riot-redis-2.5.2.zip

riot-redis-2.5.2/bin/riot-redis \
  -h <something>.cache.amazonaws.com \
  replicate \
    -h <something_else>.cache.amazonaws.com \
    --live \
    --reader-threads=10 \
    --reader-batch=2000 \
    --reader-queue 100000 \
    --threads=8 \
    --batch=2000
```

RIOT reached a rate of ~120,000 keys / second in tests. Further tuning of RIOT
parameters might provide even higher throughput.

Note: If you want to synchronize live edits to the source cluster, you must use a custom
ElastiCache Redis parameter group with `notify-keyspace-events: KA` option. CloudFormation
stacks included in this setup include this option.

### Upgrade Testing

The `redis-cluster-legacy` template deploys a Redis cluster that uses
previous generation instances and old Redis. You can use that to test
upgrades of Redis and instances.

#### Upgrading Redis to Latest Version

CloudFormation performs an in-place upgrade if you change the Redis
version. ElastiCache retains data you have in the cluster during
the upgrade.

ElastiCache seems to upgrade Redis in-place on the current instance. They
appear to dump data to disk, upgrade Redis and start Redis from the dump.

Redis will be unavailable during the upgrade (at least with a single node
cluster). It refuses connections and responds with errors while it's loading
data back into memory. Once complete, Redis continues to serve clients
normally.

#### Changing Redis Instance Type

CloudFormation performs an in-place upgrade if you change the instance
type. ElastiCache retains data you have in the cluster during the upgrade.

If the new instance does not have enough memory to hold all the data you
have in your current instance, upgrade fails with

> Failed applying modification to cache node type to Cache Cluster <cluster_id>

event in ElastiCache console. CloudFormation does not detect this failure
and marks stack update successful.

You can check the amount of memory the data in your Redis cluster needs
by running

```
redis-cli -h <something>.cache.amazonaws.com info memory | grep used_memory_dataset
```

It's not entirely clear which metric ElastiCache uses to determine if an instance
type change is allowed or not. But if you delete some data from your current instance,
ElastiCache allows you to change the node type to one with less memory.

Here's a simple command to drop 1,000,000 random(ish) keys from your Redis cluster:

```
redis-cli -h <something>.cache.amazonaws.com --scan \
| head -1000000 \
| sed "s/^/DEL /g" \
| redis-cli -h <something>.cache.amazonaws.com --pipe
```

ElastiCache allows an upgrade to start when it determines the new instance type
has enough memory to fit all the data from the current instance.

During the upgrade, Redis continues to serve traffic normally. ElastiCache seems to
spin up a new Redis instance and replicate data in the background. When the new instance
is ready, ElastiCache fails the cluster over to the new instance. Downtime is short and
no data is lost during upgrade.

## Cleanup

Cleanup resources by deleting all CloudFormation stacks in reverse order from deployment:

```bash
# Redis clusters
make -j delete-redis-cluster delete-redis-cluster-legacy

# Workspace Node
make delete-ec2-workspace
```

## Links and Credits

* Sticker Mule / Rump
  * https://github.com/stickermule/rump

* Redis Labs / RIOT
  * https://developer.redislabs.com/riot/
  * https://github.com/redis-developer/riot

* Amazon ElastiCache for Redis Documentation
  * https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/WhatIs.html
  * https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/AWS_ElastiCache.html

## License

MIT.
