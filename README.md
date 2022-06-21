# Trade Zoo

[![main](https://github.com/skupperproject/skupper-example-trade-zoo/actions/workflows/main.yaml/badge.svg)](https://github.com/skupperproject/skupper-example-trade-zoo/actions/workflows/main.yaml)

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
* [Accessing the web console](#accessing-the-web-console)
* [Cleaning up](#cleaning-up)

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
[kubeconfig][kubeconfig] and current context to select the
namespace where it operates.

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

_**Console for public:**_

~~~ shell
export KUBECONFIG=~/.kube/config-public
~~~

_**Console for private:**_

~~~ shell
export KUBECONFIG=~/.kube/config-private
~~~

## Step 2: Access your clusters

The methods for accessing your clusters vary by Kubernetes
provider. Find the instructions for your chosen providers and use
them to authenticate and configure access for each console
session.  See the following links for more information:

* [Minikube](https://skupper.io/start/minikube.html)
* [Amazon Elastic Kubernetes Service (EKS)](https://skupper.io/start/eks.html)
* [Azure Kubernetes Service (AKS)](https://skupper.io/start/aks.html)
* [Google Kubernetes Engine (GKE)](https://skupper.io/start/gke.html)
* [IBM Kubernetes Service](https://skupper.io/start/ibmks.html)
* [OpenShift](https://skupper.io/start/openshift.html)
* [More providers](https://kubernetes.io/partners/#kcsp)

## Step 3: Set up your namespaces

Use `kubectl create namespace` to create the namespaces you wish
to use (or use existing namespaces).  Use `kubectl config
set-context` to set the current namespace for each session.

_**Console for public:**_

~~~ shell
kubectl create namespace public
kubectl config set-context --current --namespace public
~~~

_Sample output:_

~~~ console
$ kubectl create namespace public
namespace/public created

$ kubectl config set-context --current --namespace public
Context "minikube" modified.
~~~

_**Console for private:**_

~~~ shell
kubectl create namespace private
kubectl config set-context --current --namespace private
~~~

_Sample output:_

~~~ console
$ kubectl create namespace private
namespace/private created

$ kubectl config set-context --current --namespace private
Context "minikube" modified.
~~~

## Step 4: Install Skupper in your namespaces

The `skupper init` command installs the Skupper router and service
controller in the current namespace.  Run the `skupper init` command
in each namespace.

**Note:** If you are using Minikube, [you need to start `minikube
tunnel`][minikube-tunnel] before you install Skupper.

[minikube-tunnel]: https://skupper.io/start/minikube.html#running-minikube-tunnel

_**Console for public:**_

~~~ shell
skupper init
~~~

_Sample output:_

~~~ console
$ skupper init
Waiting for LoadBalancer IP or hostname...
Skupper is now installed in namespace 'public'.  Use 'skupper status' to get more information.
~~~

_**Console for private:**_

~~~ shell
skupper init
~~~

_Sample output:_

~~~ console
$ skupper init
Waiting for LoadBalancer IP or hostname...
Skupper is now installed in namespace 'private'.  Use 'skupper status' to get more information.
~~~

## Step 5: Check the status of your namespaces

Use `skupper status` in each console to check that Skupper is
installed.

_**Console for public:**_

~~~ shell
skupper status
~~~

_Sample output:_

~~~ console
$ skupper status
Skupper is enabled for namespace "public" in interior mode. It is connected to 1 other site. It has 1 exposed service.
The site console url is: <console-url>
The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
~~~

_**Console for private:**_

~~~ shell
skupper status
~~~

_Sample output:_

~~~ console
$ skupper status
Skupper is enabled for namespace "private" in interior mode. It is connected to 1 other site. It has 1 exposed service.
The site console url is: <console-url>
The credentials for internal console-auth mode are held in secret: 'skupper-console-users'
~~~

As you move through the steps below, you can use `skupper status` at
any time to check your progress.

## Step 6: Link your namespaces

Creating a link requires use of two `skupper` commands in
conjunction, `skupper token create` and `skupper link create`.

The `skupper token create` command generates a secret token that
signifies permission to create a link.  The token also carries the
link details.  Then, in a remote namespace, The `skupper link
create` command uses the token to create a link to the namespace
that generated it.

**Note:** The link token is truly a *secret*.  Anyone who has the
token can link to your namespace.  Make sure that only those you
trust have access to it.

First, use `skupper token create` in one namespace to generate the
token.  Then, use `skupper link create` in the other to create a
link.

_**Console for public:**_

~~~ shell
skupper token create ~/secret.token
~~~

_Sample output:_

~~~ console
$ skupper token create ~/secret.token
Token written to ~/secret.token
~~~

_**Console for private:**_

~~~ shell
skupper link create ~/secret.token
~~~

_Sample output:_

~~~ console
$ skupper link create ~/secret.token
Site configured to link to https://10.105.193.154:8081/ed9c37f6-d78a-11ec-a8c7-04421a4c5042 (name=link1)
Check the status of the link using 'skupper link status'.
~~~

If your console sessions are on different machines, you may need
to use `sftp` or a similar tool to transfer the token securely.
By default, tokens expire after a single use or 15 minutes after
creation.

## Step 7: Deploy the Kafka cluster

In the private namespace, use the `kubectl create` and `kubectl
apply` commands with the listed YAML files to install the
operator and deploy the cluster and topic.

_**Console for private:**_

~~~ shell
kubectl create -f kafka-cluster/strimzi.yaml
kubectl apply -f kafka-cluster/cluster1.yaml
kubectl wait --for condition=ready --timeout 900s kafka/cluster1
~~~

## Step 8: Expose the Kafka cluster

In the private namespace, use `skupper expose` with the
`--headless` option to expose the Kafka cluster as a headless
service on the Skupper network.

Then, in the public namespace, use `kubectl get service` to
check that the `cluster1-kafka-brokers` service appears after a
moment.

_**Console for private:**_

~~~ shell
skupper expose statefulset/cluster1-kafka --headless --port 9092
~~~

_**Console for public:**_

~~~ shell
kubectl get service/cluster1-kafka-brokers
~~~

**Note:**

By default, the Kafka bootstrap server returns broker addresses
that include the Kubernetes namespace in their domain name.
When, as in this example, the Kafka client is running in a
namespace with a different name from that of the Kafka cluster,
this prevents the client from resolving the Kafka brokers.

To make the Kafka brokers reachable, set the `advertisedHost`
property of each broker to a domain name that the Kafka client
can resolve at the remote site.  In this example, this is
achieved with the following listener configuration:

~~~ yaml
spec:
  kafka:
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
        configuration:
          brokers:
            - broker: 0
              advertisedHost: cluster1-kafka-0.cluster1-kafka-brokers
~~~

See [Advertised addresses for brokers][advertised-addresses] for
more information.

[advertised-addresses]: https://strimzi.io/docs/operators/in-development/configuring.html#property-listener-config-broker-reference

## Step 9: Deploy the application services

In the public namespace, use the `kubectl apply` command with
the listed YAML files to install the application services.

_**Console for public:**_

~~~ shell
kubectl apply -f order-processor/kubernetes.yaml
kubectl apply -f market-data/kubernetes.yaml
kubectl apply -f frontend/kubernetes.yaml
~~~

## Step 10: Test the application

Now we're ready to try it out.  Use `kubectl get service/frontend`
to look up the external IP of the frontend service.  Then use
`curl` or a similar tool to request the `/api/health` endpoint at
that address.

**Note:** The `<external-ip>` field in the following commands is a
placeholder.  The actual value is an IP address.

_**Console for public:**_

~~~ shell
kubectl get service/frontend
curl http://<external-ip>:8080/api/health
~~~

_Sample output:_

~~~ console
$ kubectl get service/frontend
NAME       TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)          AGE
frontend   LoadBalancer   10.103.232.28   <external-ip>   8080:30407/TCP   15s

$ curl http://<external-ip>:8080/api/health
OK
~~~

If everything is in order, you can now access the web interface by
navigating to `http://<external-ip>:8080/` in your browser.

## Accessing the web console

Skupper includes a web console you can use to view the application
network.  To access it, use `skupper status` to look up the URL of
the web console.  Then use `kubectl get
secret/skupper-console-users` to look up the console admin
password.

**Note:** The `<console-url>` and `<password>` fields in the
following output are placeholders.  The actual values are specific
to your environment.

_**Console for public:**_

~~~ shell
skupper status
kubectl get secret/skupper-console-users -o jsonpath={.data.admin} | base64 -d
~~~

_Sample output:_

~~~ console
$ skupper status
Skupper is enabled for namespace "public" in interior mode. It is connected to 1 other site. It has 1 exposed service.
The site console url is: <console-url>
The credentials for internal console-auth mode are held in secret: 'skupper-console-users'

$ kubectl get secret/skupper-console-users -o jsonpath={.data.admin} | base64 -d
<password>
~~~

Navigate to `<console-url>` in your browser.  When prompted, log
in as user `admin` and enter the password.

## Cleaning up

To remove Skupper and the other resources from this exercise, use
the following commands.

_**Console for private:**_

~~~ shell
skupper delete
kubectl delete -f kafka-cluster/cluster1.yaml
kubectl delete -f kafka-cluster/strimzi.yaml
~~~

_**Console for public:**_

~~~ shell
skupper delete
kubectl delete -f frontend/kubernetes.yaml
kubectl delete -f market-data/kubernetes.yaml
kubectl delete -f order-processor/kubernetes.yaml
~~~

## Next steps


Check out the other [examples][examples] on the Skupper website.
