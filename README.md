# Kubernetes LDAP authentication

This is a Kubernetes LDAP authentication service.  It allows the Kubernetes
API server to authenticate users against an LDAP directory.  Only authentication
is supported, not authorization.  It will work fine with RBAC, WebHook
authorization, or any other authorization method that deals with users and
groups.

## Directory requirements

The token is expected to be stored in an LDAP attribute such as
`kubernetesToken`.  Authenticating against `userPassword` is not supported.
(Because `kubectl` stores the password unencrypted in its configuration file,
this would be quite insecure.)

A sample schema might look like this:

```
attributeType ( 1.3.6.1.4.1.18171.2.1.8
        NAME 'kubernetesToken'
        DESC 'Kubernetes authentication token'
        EQUALITY caseExactIA5Match
        SUBSTR caseExactIA5SubstringsMatch
        SYNTAX 1.3.6.1.4.1.1466.115.121.1.26 SINGLE-VALUE )

objectClass ( 1.3.6.1.4.1.18171.2.3
        NAME 'kubernetesAuthenticationObject'
        DESC 'Object that may authenticate to a Kubernetes cluster'
        AUXILIARY
        MUST kubernetesToken )
```

We have allocated the OIDs above for these schema types, so you can use them in
your own schema if you like (although there is no requirement to do so).

## Setup

Copy `config.py.example` to `config.py` and edit it for your site.

Create a secret containing the configuration:

```
$ kubectl -n kube-system create secret generic ldap-authn-config \
        --from-file=config.py=config.py
```

Or if your LDAP server requires a CA certificate:

```
$ kubectl -n kube-system create secret generic ldap-authn-config \
        --from-file=config.py=config.py --from-file=ca-cert.pem=my-ca-cert.pem
```

Deploy the DaemonSet:

```
$ kubectl apply -f daemonset.yaml
```

Create a `kubeconfig` on the master with the connection details:

```
clusters:
  - name: ldap-authn
    cluster:
      server: http://localhost:8087/authn
users:
  - name: apiserver
current-context: webhook
contexts:
- context:
    cluster: ldap-authn
    user: apiserver
  name: webhook
```

Configure kube-apiserver to use webhook authentication by passing
`--authentication-token-webhook-config-file=/path/to/my/webhook-auth-kubeconfig`.

## Client setup

Configure `kubectl` to use your LDAP token:

```
$ kubectl config set-cluster mycluster --server=https://myapiserver.com/ [...]
$ kubectl config set-credentials mycluster-ldap --token="my-ldap-token"
$ kubectl config set-context mycluster --cluster=mycluster --user=mycluster-ldap
```
