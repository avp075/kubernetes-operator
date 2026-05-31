# Kubernetes Namespace Operator

A lightweight Kubernetes operator that automatically manages team namespaces, applies resource quotas, and cleans up namespaces when they are removed from the custom resource.

## What it does

- Defines a cluster-scoped CRD: `NamespaceSet` in `example.com/v1`
- Creates namespaces for each team in the CRD using the naming scheme `<team>-<namespace>`
- Adds labels to track managed namespaces:
  - `managed-by=namespace-operator`
  - `owner-team=<team>`
  - `ns-type=<namespace type>`
- Creates or updates a `ResourceQuota` named `rq-<namespace>` for each namespace
- Deletes managed namespaces that are no longer present in the active `NamespaceSet`
- Sends Slack notifications for namespace creation and deletion events

<img width="1398" height="657" alt="Screenshot 2026-05-31 215229" src="https://github.com/user-attachments/assets/d2cb78a9-c66b-40de-adcd-77872b642723" />


## Repository structure

```
kubernetes-operator/
├── Dockerfile
├── README.md
├── custom-resource-definition.yaml
├── custom-resource.yaml
├── deploy.yaml
├── name-space-operator.py
└── rbac.yaml
```

## Automation (GitOps)

This namespace management process can be fully automated by storing the `NamespaceSet` manifest in a Git repository and using a GitOps tool (for example, Argo CD) to continuously deploy it along with the operator. Integrating with Argo CD or another GitOps solution keeps the desired state in version control and enables automated rollouts, audits, and rollbacks.

## Files

- `name-space-operator.py` - operator logic implemented using Kopf
- `custom-resource-definition.yaml` - CRD definition for `NamespaceSet`
- `custom-resource.yaml` - example `NamespaceSet`
- `deploy.yaml` - deployment manifest for the operator
- `rbac.yaml` - service account and cluster role binding

## Prerequisites

- Kubernetes cluster with `kubectl` access
- A container registry or local image build for the operator
- Python operator runtime image with Kopf installed (or use the published image referenced in `deploy.yaml`)

## Deploy the operator

1. Apply the CRD:

```bash
kubectl apply -f custom-resource-definition.yaml
```

2. Create RBAC resources:

```bash
kubectl apply -f rbac.yaml
```

3. Deploy the operator:

```bash
kubectl apply -f deploy.yaml
```

## Use the operator

Create a `NamespaceSet` resource to define teams, namespaces, and quotas.

```bash
kubectl apply -f custom-resource.yaml
```

The operator will create namespaces named like `team1-dev`, `team1-test`, `team2-dev`, and `team2-test`.

## Custom resource structure

Example `NamespaceSet` structure:

```yaml
apiVersion: example.com/v1
kind: NamespaceSet
metadata:
  name: example-namespace-set
spec:
  teams:
    - name: team1
      email: team1@example.com
      namespaces:
        - dev
        - test
      resourceQuota:
        hard:
          requests.cpu: "1"
          requests.memory: "1Gi"
          limits.cpu: "2"
          limits.memory: "2Gi"
    - name: team2
      email: team2@example.com
      namespaces:
        - dev
        - test
      resourceQuota:
        hard:
          requests.cpu: "500m"
          requests.memory: "512Mi"
          limits.cpu: "1"
          limits.memory: "1Gi"
```

## Verify managed namespaces

```bash
kubectl get namespaces -l managed-by=namespace-operator
kubectl describe namespace team1-dev
```

## Notes

- The operator sends Slack notifications using the webhook URL configured in `name-space-operator.py`.
- The deployment uses the image `aviral tzu/namespace-operator:latest`; update the image name as needed for your registry.
- The operator requires cluster-wide permissions because it creates namespaces and manages cluster-scoped resources.

## Troubleshooting

- If namespaces are not created, confirm the CRD exists and the operator pod is running.
- Check operator logs:

```bash
kubectl logs deploy/namespace-operator
```

- If namespace cleanup does not happen, ensure the `NamespaceSet` resource has the correct `teams` and `namespaces` entries.


