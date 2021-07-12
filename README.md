# Trade Zoo with Kafka and Skupper

[![main](https://github.com/ssorj/skupper-example-kafka/actions/workflows/main.yaml/badge.svg)](https://github.com/ssorj/skupper-example-kafka/actions/workflows/main.yaml)

#### A simple trading application that runs in the public cloud but keeps its data in a private Kafka cluster

This example is part of a [suite of examples][examples] showing the
different ways you can use [Skupper][website] to connect services
across cloud providers, data centers, and edge sites.

[website]: https://skupper.io/
[examples]: https://skupper.io/examples/index.html

#### Contents

* [Overview](#overview)
* [Prerequisites](#prerequisites)
* [Step 1: Configure separate console sessions](#step-1-configure-separate-console-sessions)
* [Step 2: Log in to your clusters](#step-2-log-in-to-your-clusters)
* [Step 3: Set up your namespaces](#step-3-set-up-your-namespaces)
* [Step 4: Install Skupper in your namespaces](#step-4-install-skupper-in-your-namespaces)
* [Step 5: Link your namespaces](#step-5-link-your-namespaces)
* [Step 6: Deploy the Kafka cluster](#step-6-deploy-the-kafka-cluster)
* [Step 7: Expose the Kafka cluster](#step-7-expose-the-kafka-cluster)
* [Step 8: Deploy the application services](#step-8-deploy-the-application-services)
* [Cleaning up](#cleaning-up)
* [Next steps](#next-steps)

## Overview

This example is a simple Kafka application that shows how you can
use Skupper to access a Kafka cluster at a remote site without
exposing it to the public internet.

It contains four services:

* A Kafka cluster running in a private data center.  The cluster has
  two topics, "orders" and "updates".

* An order processor running in the public cloud.  It consumes from
  "orders", matching buy and sell offers to make trades.  It
  publishes new and updated orders and trades to "updates".

* A market data service running in the public cloud.  It looks at
  the completed trades and computes the latest and average prices,
  which it then publishes to "updates".

* A web frontend service running in the public cloud.  It submits
  buy and sell orders to "orders" and consumes from "updates" in
  order to show what's happening.

To set up the Kafka cluster, this example uses the Kubernetes
operator from the [Strimzi][strimzi] project.  The other services
are small Python programs.

The example uses two Kubernetes namespaces, "private" and "public",
to represent the private data center and public cloud.

[strimzi]: https://strimzi.io/
[quarkus]: https://quarkus.io/

## Prerequisites

* The `kubectl` command-line tool, version 1.15 or later
  ([installation guide][install-kubectl])

* The `skupper` command-line tool, the latest version ([installation
  guide][install-skupper])

* Access to two Kubernetes namespaces, from any providers you choose,
  on any clusters you choose

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-skupper]: https://skupper.io/start/index.html#step-1-install-the-skupper-command-line-tool-in-your-environment

## Step 1: Configure separate console sessions

Skupper is designed for use with multiple namespaces, typically on
different clusters.  The `skupper` command uses your
[kubeconfig][kubeconfig] and current context to select the namespace
where it operates.

[kubeconfig]: https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/

Your kubeconfig is stored in a file in your home directory.  The
`skupper` and `kubectl` commands use the `KUBECONFIG` environment
variable to locate it.

A single kubeconfig supports only one active context per user.
Since you will be using multiple contexts at once in this
exercise, you need to create distinct kubeconfigs.

Start a console session for each of your namespaces.  Set the
`KUBECONFIG` environment variable to a different path in each
session.

Console for _public_:

~~~ shell
export KUBECONFIG=~/.kube/config-public
~~~

Console for _private_:

~~~ shell
export KUBECONFIG=~/.kube/config-private
~~~

## Step 2: Log in to your clusters

The methods for logging in vary by Kubernetes provider.  Find
the instructions for your chosen providers and use them to
authenticate and configure access for each console session.  See
the following links for more information:

* [Minikube](https://skupper.io/start/minikube.html#logging-in)
* [Amazon Elastic Kubernetes Service (EKS)](https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html)
* [Azure Kubernetes Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/kubernetes-walkthrough#connect-to-the-cluster)
* [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html#logging-in)
* [IBM Kubernetes Service](https://skupper.io/start/ibmks.html#logging-in)
* [OpenShift](https://skupper.io/start/openshift.html#logging-in)

## Step 3: Set up your namespaces

Use `kubectl create namespace` to create the namespaces you wish to
use (or use existing namespaces).  Use `kubectl config set-context` to
set the current namespace for each session.

Console for _public_:

~~~ shell
kubectl create namespace public
kubectl config set-context --current --namespace public
~~~

Console for _private_:

~~~ shell
kubectl create namespace private
kubectl config set-context --current --namespace private
~~~

## Step 4: Install Skupper in your namespaces

The `skupper init` command installs the Skupper router and service
controller in the current namespace.  Run the `skupper init` command
in each namespace.

[minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel

**Note:** If you are using Minikube, [you need to start `minikube
tunnel`][minikube-tunnel] before you install Skupper.

Console for _public_:

~~~ shell
skupper init
~~~

Console for _private_:

~~~ shell
skupper init --ingress none
~~~

## Step 5: Link your namespaces

Creating a link requires use of two `skupper` commands in conjunction,
`skupper token create` and `skupper link create`.

The `skupper token create` command generates a secret token that
signifies permission to create a link.  The token also carries the
link details.  The `skupper link create` command then uses the link
token to create a link to the namespace that generated it.

**Note:** The link token is truly a *secret*.  Anyone who has the
token can link to your namespace.  Make sure that only those you trust
have access to it.

First, use `skupper token create` in one namespace to generate the
token.  Then, use `skupper link create` in the other to create a link.

Console for _public_:

~~~ shell
skupper token create ~/public.token
~~~

Console for _private_:

~~~ shell
skupper link create ~/public.token
skupper link status --wait 30
~~~

## Step 6: Deploy the Kafka cluster

In the private namespace, use the `kubectl create` and `kubectl
apply` commands with the listed YAML files to install the
operator and deploy the cluster and topic.

Console for _private_:

~~~ shell
kubectl create -f kafka-cluster/strimzi.yaml
kubectl apply -f kafka-cluster/cluster1.yaml
kubectl wait --for condition=ready --timeout 540s kafka/cluster1
~~~

## Step 7: Expose the Kafka cluster

In the private namespace, use `skupper expose` with the
`--headless` option to expose the Kafka cluster as a headless
service on the Skupper network.

Then, in the public namespace, use `kubectl get services` to
check that the `cluster1-kafka-brokers` service appears after a
moment.

Console for _private_:

~~~ shell
skupper expose statefulset/cluster1-kafka --headless --port 9092
~~~

Console for _public_:

~~~ shell
kubectl get services
~~~

## Step 8: Deploy the application services

Console for _public_:

~~~ shell
kubectl apply -f order-processor/kubernetes.yaml
kubectl apply -f market-data/kubernetes.yaml
kubectl apply -f frontend/kubernetes.yaml
~~~

## Cleaning up

To remove Skupper and the other resources from this exercise, use the
following commands.

Console for _private_:

~~~ shell
skupper delete
kubectl delete -f kafka-cluster/cluster1.yaml
kubectl delete -f kafka-cluster/strimzi.yaml
~~~

Console for _public_:

~~~ shell
skupper delete
kubectl delete -f frontend/kubernetes.yaml
kubectl delete -f market-data/kubernetes.yaml
kubectl delete -f order-processor/kubernetes.yaml
~~~

## Next steps

Check out the other [examples][examples] on the Skupper website.
