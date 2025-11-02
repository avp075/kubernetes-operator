![Kubernetes Namespace Automation with Slack](https://github.com/user-attachments/assets/db57b24c-4333-46f9-b1f5-faaa03d07f2c)


'''
➜  namespace-operator git:(main) kubectl describe ns team1-dev
Name:         team1-dev
Labels:       kubernetes.io/metadata.name=team1-dev
              managed-by=namespace-operator
              ns-type=dev
              owner-team=team1
Annotations:  <none>
Status:       Active

Resource Quotas
  Name:            rq-team1-dev
  Resource         Used  Hard
  --------         ---   ---
  limits.cpu       0     2
  limits.memory    0     2Gi
  requests.cpu     0     1
  requests.memory  0     1Gi

No LimitRange resource.
➜  namespace-operator git:(main)
'''
