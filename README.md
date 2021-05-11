# fastrak
Tools and experiments for providing out-of-the-box dev-friendly support for persistent storage and LB services on Platform9 Managed Kubernetes.

## Local Volume Provisioner

This hack is a Python script that runs on every node (preferably as a daemon set, but it was locally and manually launched for the hackathon).
- It periodically polls Kubernetes API server for persistent volume claims (PVCs) that are Pending.
- For each pending PVC, it computes a persistent volume (PV) name unique to the node by appending the node host name to the PVC name and sanitizing it.
- It creates a local directory with that name.
- It creates a local PV with that directory name and a capacity that matches exactly what's requested by the PVC.
- If all goes well, the PVC should bind to the PV, provided that the storage class resource is created beforehand (see below)
- The script also periodically cleans up Released PVs that are no longer bound.

### Storage Class Resource

The include YAML file defines a storage class with name "local-storage" and makes it the default one for PVCs that don't specify a storage class. It should be installed first.

### Known Issues and Alternatives

- This is a hack, and it has many technical issues and limitations. For example, the script doesn't actually check to see if the local node has enough disk space to accommodate the requested PVC capacity. This is just a proof of concept.
- The better longer term solution is probably to use CSI + ExternalProvisioner + Hostpath plugin (which is not production ready at this point)

## SaaS LoadBalancer

Several options were investigated as a simpler OOB alternative to MetalLB:
1. Using the local node's IP(s) in the case of a single-node cluster
1. SaaS tunneling using ngrok
1. SaaS tunneling using inlets Pro

- (1) turned out to be difficult because we can't use the node's existing IPs due to port conflicts (the service resource dictates the port number). This deserves another look later, possibly using dynamically created IPs (a.k.a. IP aliasing) from an available unused subnet.
- (2) is impossible for the same reason: ngrok uses a small number of public IPs and multiplexes many connections using different random ports.

We ended up using (3) because inlets Pro's operator creates one dedicated VM instance ("exit node") per service resource, with its own unique public IP. 


