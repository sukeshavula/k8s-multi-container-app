# k8s-multi-container-app

Small lab for getting hands-on with Kubernetes on Minikube: a Flask app (3 replicas) that counts visits in Redis. Redis stores its data on a PVC, and traffic comes in through the NGINX ingress.

The app itself isn't the point. I wanted something with a stateful piece and a stateless piece so I could break things and see how Kubernetes reacts.

![ci](https://github.com/sukeshavula/k8s-multi-container-app/actions/workflows/ci.yml/badge.svg)

```
app/                    Flask + gunicorn, non-root image
k8s/00-namespace.yaml
k8s/10-redis.yaml       PVC + Redis (appendonly) + Service
k8s/20-web.yaml         ConfigMap, Deployment (probes, limits), Service, Ingress
```

## Run it

```bash
minikube start
minikube addons enable ingress
minikube image build -t visits-web:1.0 app/     # builds straight into minikube, no registry

kubectl apply -f k8s/
kubectl -n visits get pods -w

echo "$(minikube ip) visits.local" | sudo tee -a /etc/hosts
curl http://visits.local/
```

On Windows with the Docker driver, `minikube ip` isn't reachable. Run `minikube tunnel` and map `127.0.0.1 visits.local` in `C:\Windows\System32\drivers\etc\hosts` instead.

## Things I'm testing

**Does the count survive Redis being killed?**
```bash
kubectl -n visits delete pod -l app=redis
curl -s http://visits.local/
```
It should, because the PVC outlives the pod and appendonly replays the log on startup.

**What readiness actually does**
```bash
kubectl -n visits scale deploy redis --replicas=0
kubectl -n visits get pods     # web pods go 0/1
curl -i http://visits.local/   # 503, no ready endpoints
kubectl -n visits scale deploy redis --replicas=1
```
`/readyz` fails without Redis, so the pods drop out of the Service. Liveness only checks `/healthz`, so they don't get restarted. That's why the two probes are separate.

**Broken ingress:** point the ingress backend at a service that doesn't exist, then look at `kubectl describe ingress` and the controller logs.

**Rollout with no dropped requests:** `kubectl rollout restart deploy/web` with a curl loop running. `maxUnavailable: 0` should mean no failures.

Also: `Recreate` on the Redis deployment is intentional. The PVC is ReadWriteOnce, so a rolling update would leave the new pod stuck waiting for the volume.

## Notes

Results of the tests above get written up here as I run them.

## TODO

- [ ] HPA on CPU (needs `minikube addons enable metrics-server`)
- [ ] Turn it into a Helm chart
- [ ] Try it on EKS with the AWS Load Balancer Controller and EBS volumes
