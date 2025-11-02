"""
Namespace Operator using Kopf
- Cluster scoped CRD: NamespaceSet (example.com/v1)
- Ensures namespaces for each team are present as <team>-<ns>
- Applies a ResourceQuota to each created namespace
- Labels namespaces it manages so it can safely delete them when removed from the CR
- Logs actions
"""

import kopf
import kubernetes
import logging
import os
import time
from kubernetes.client import V1Namespace, V1ObjectMeta, V1ResourceQuota, V1ResourceQuotaSpec

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(level=LOG_LEVEL, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('namespace-operator')

# Labels used to mark managed namespaces
MANAGED_BY_LABEL = 'managed-by'
MANAGED_BY_VALUE = 'namespace-operator'
OWNER_TEAM_LABEL = 'owner-team'
NS_TYPE_LABEL = 'ns-type'

# Namespace name format: <team>-<ns>
def ns_name_for(team: str, ns: str) -> str:
    return f"{team.lower()}-{ns.lower()}"


def ensure_namespace(api, name: str, team: str, ns_type: str, resource_quota_spec: dict | None):
    try:
        api.read_namespace(name)
        logger.info(f"Namespace exists: {name}")
    except kubernetes.client.exceptions.ApiException as e:
        if e.status == 404:
            logger.info(f"Creating namespace: {name}")
            meta = V1ObjectMeta(name=name, labels={MANAGED_BY_LABEL: MANAGED_BY_VALUE, OWNER_TEAM_LABEL: team, NS_TYPE_LABEL: ns_type})
            ns_body = V1Namespace(metadata=meta)
            api.create_namespace(ns_body)
            # give k8s a moment before creating quota
            time.sleep(0.5)
        else:
            raise

    # apply resource quota (create or replace)
    if resource_quota_spec:
        try:
            v1 = kubernetes.client.CoreV1Api()
            rq_name = 'rq-' + name
            # Build ResourceQuota object
            spec = V1ResourceQuotaSpec(hard=resource_quota_spec.get('hard'))
            rq_body = V1ResourceQuota(metadata=V1ObjectMeta(name=rq_name, namespace=name), spec=spec)
            # Try to read existing
            try:
                existing = v1.read_namespaced_resource_quota(rq_name, name)
                # patch/replace
                v1.replace_namespaced_resource_quota(rq_name, name, rq_body)
                logger.info(f"Updated ResourceQuota {rq_name} in {name}")
            except kubernetes.client.exceptions.ApiException as e:
                if e.status == 404:
                    v1.create_namespaced_resource_quota(name, rq_body)
                    logger.info(f"Created ResourceQuota {rq_name} in {name}")
                else:
                    raise
        except Exception:
            logger.exception(f"Failed to ensure ResourceQuota in {name}")


def list_managed_namespaces(api):
    ns_list = api.list_namespace(label_selector=f"{MANAGED_BY_LABEL}={MANAGED_BY_VALUE}")
    result = {}
    for item in ns_list.items:
        labels = item.metadata.labels or {}
        team = labels.get(OWNER_TEAM_LABEL, 'unknown')
        ns_type = labels.get(NS_TYPE_LABEL, 'unknown')
        result[item.metadata.name] = {'team': team, 'ns_type': ns_type}
    return result


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_):
    # allow longer duration for slow clusters
    settings.posting.level = logging.INFO
    kubeconfig = os.getenv('KUBECONFIG')
    kubernetes.config.load_incluster_config() if not kubeconfig else kubernetes.config.load_kube_config()
    logger.info('Loaded Kubernetes configuration')


@kopf.on.create('example.com', 'v1', 'namespacesets')
@kopf.on.update('example.com', 'v1', 'namespacesets')
@kopf.on.resume('example.com', 'v1', 'namespacesets')
def reconcile(body, spec, **kwargs):
    api = kubernetes.client.CoreV1Api()
    desired = {}
    teams = spec.get('teams', []) if spec else []

    # Build desired mapping: namespace_name -> (team, ns_type, resourceQuotaSpec)
    for team in teams:
        team_name = team.get('name')
        if not team_name:
            continue
        rq = team.get('resourceQuota') or {}
        for ns in team.get('namespaces', []):
            name = ns_name_for(team_name, ns)
            desired[name] = {'team': team_name, 'ns_type': ns, 'resourceQuota': rq}

    # Ensure desired namespaces exist
    for name, meta in desired.items():
        try:
            ensure_namespace(api, name, meta['team'], meta['ns_type'], meta['resourceQuota'])
        except Exception:
            logger.exception(f"Error ensuring namespace {name}")

    # Delete managed namespaces that are no longer desired
    managed = list_managed_namespaces(api)
    for existing_ns, info in managed.items():
        if existing_ns not in desired:
            # delete namespace
            try:
                logger.info(f"Deleting namespace no longer in CR: {existing_ns}")
                api.delete_namespace(existing_ns)
            except Exception:
                logger.exception(f"Failed to delete namespace {existing_ns}")

    # update status with counts
    status = {'managedNamespaces': len(desired)}
    return {'status': status}


#@kopf.on.delete('example.com', 'v1', 'namespacesets')
def on_cr_delete(spec, **kwargs):
    # When the CR itself is deleted, remove all namespaces we managed for the teams defined in the CR
    api = kubernetes.client.CoreV1Api()
    teams = spec.get('teams', []) if spec else []
    to_delete = []
    for team in teams:
        tname = team.get('name')
        if not tname:
            continue
        for ns in team.get('namespaces', []):
            nn = ns_name_for(tname, ns)
            to_delete.append(nn)

    for ns in to_delete:
        try:
            logger.info(f"Deleting namespace as CR removed: {ns}")
            api.delete_namespace(ns)
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info(f"Namespace already gone: {ns}")
            else:
                logger.exception(f"Failed to delete {ns}")

