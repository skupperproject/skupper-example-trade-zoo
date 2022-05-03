# Trade Zoo

[![main](https://github.com/ssorj/skupper-example-trade-zoo/actions/workflows/main.yaml/badge.svg)](https://github.com/ssorj/skupper-example-trade-zoo/actions/workflows/main.yaml)

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
* [Step 2: Access your clusters](#step-2-access-your-clusters)
* [Step 3: Set up your namespaces](#step-3-set-up-your-namespaces)
* [Step 4: Install Skupper in your namespaces](#step-4-install-skupper-in-your-namespaces)
* [Step 5: Check the status of your namespaces](#step-5-check-the-status-of-your-namespaces)
* [Step 6: Link your namespaces](#step-6-link-your-namespaces)
* [Step 7: Deploy the Kafka cluster](#step-7-deploy-the-kafka-cluster)
* [Step 8: Expose the Kafka cluster](#step-8-expose-the-kafka-cluster)
* [Step 9: Deploy the application services](#step-9-deploy-the-application-services)
* [Step 10: Test the application](#step-10-test-the-application)
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

* Access to at least one Kubernetes cluster, from any provider you
  choose

[install-kubectl]: https://kubernetes.io/docs/tasks/tools/install-kubectl/
[install-skupper]: https://skupper.io/install/index.html

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

## Step 2: Access your clusters

The methods for accessing your clusters vary by Kubernetes provider.
Find the instructions for your chosen providers and use them to
authenticate and configure access for each console session.  See the
following links for more information:

* [Minikube](https://skupper.io/start/minikube.html)
* [Amazon Elastic Kubernetes Service (EKS)](https://skupper.io/start/eks.html)
* [Azure Kubernetes Service (AKS)](https://skupper.io/start/aks.html)
* [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html)
* [IBM Kubernetes Service](https://skupper.io/start/ibmks.html)
* [OpenShift](https://skupper.io/start/openshift.html)
* [More providers](https://kubernetes.io/partners/#kcsp)

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

**Note:** If you are using Minikube, [you need to start `minikube
tunnel`][minikube-tunnel] before you install Skupper.

[minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel

Console for _public_:

~~~ shell
skupper init
~~~

Console for _private_:

~~~ shell
skupper init
~~~

## Step 5: Check the status of your namespaces

Use `skupper status` in each console to check that Skupper is
installed.

Console for _public_:

~~~ shell
skupper status
~~~

Console for _private_:

~~~ shell
skupper status
~~~

You should see output like this for each namespace:

~~~
Skupper is enabled for namespace "<namespace>" in interior mode. It is not connected to any other sites. It has no exposed services.
The site console url is: http://<address>:8080
The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
~~~

As you move through the steps below, you can use `skupper status` at
any time to check your progress.

## Step 6: Link your namespaces

Creating a link requires use of two `skupper` commands in conjunction,
`skupper token create` and `skupper link create`.

The `skupper token create` command generates a secret token that
signifies permission to create a link.  The token also carries the
link details.  Then, in a remote namespace, The `skupper link create`
command uses the token to create a link to the namespace that
generated it.

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
~~~

If your console sessions are on different machines, you may need to
use `scp` or a similar tool to transfer the token.

You can use the `skupper link status` command to see if linking
succeeded.

## Step 7: Deploy the Kafka cluster

In the private namespace, use the `kubectl create` and `kubectl
apply` commands with the listed YAML files to install the
operator and deploy the cluster and topic.

Console for _private_:

~~~ shell
kubectl create -f kafka-cluster/strimzi.yaml
kubectl apply -f kafka-cluster/cluster1.yaml
kubectl wait --for condition=ready --timeout 540s kafka/cluster1
~~~

## Step 8: Expose the Kafka cluster

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

## Step 9: Deploy the application services

In the public namespace, use the `kubectl apply` command with
the listed YAML files to install the application services.

Console for _public_:

~~~ shell
kubectl apply -f order-processor/kubernetes.yaml
kubectl apply -f market-data/kubernetes.yaml
kubectl apply -f frontend/kubernetes.yaml
~~~

## Step 10: Test the application

In the public namespace, use `kubectl get service/frontend` to
look up the external URL of the frontend service.  Then use curl
to check the `/api/health` endpoint.

Console for _public_:

~~~ shell
FRONTEND=$(kubectl get service/frontend -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:8080')
curl $FRONTEND/api/health
~~~

Sample output:

~~~
OK
~~~

If everything is in order, you can now access the application
using your browser by navigating to the external URL.

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
