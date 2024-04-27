import argparse
from collections import defaultdict, deque

from source.utils.load import load_AS_topology
from source.utils.utils import sort_dict

def get_customer_cone_for_all(as_topo):

    def get_customer_cone_for_as(asn):
        q = deque()
        q.append(asn)
        visited = defaultdict(bool)
        visited[asn] = True
        cone = 1

        while q:
            curr_asn = q.popleft()
            for cust in as_topo[curr_asn]['customers']:
                if not visited[cust]:
                    q.append(cust)
                    visited[cust] = True
                    cone += 1
        return cone

    cc_map = defaultdict(int)
    for asn in as_topo.keys():
        customer_cone = get_customer_cone_for_as(asn)
        cc_map[asn] = customer_cone
    return sort_dict(cc_map)

def get_customer_cone_size_core_ISD(isd_core_topo, isd_non_core_topo):

    def get_customer_cone_for_core_as(core_asn):
        q = deque()
        q.append(core_asn)
        visited = defaultdict(bool)
        visited[core_asn] = True
        cone = 1

        while q:
            curr_asn = q.popleft()
            for cust in isd_non_core_topo[curr_asn]['customers']:
                if not visited[cust]:
                    q.append(cust)
                    visited[cust] = True
                    cone += 1
        return cone 
    
    customer_cone_size = defaultdict(int)
    for core_asn in isd_core_topo.keys():
        customer_cone_size[core_asn] = get_customer_cone_for_core_as(core_asn)
    return customer_cone_size

################################################################################

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
    )
    parser.add_argument(
        '--save_file', default='data/scion/20230101.customer-cone-size.txt'
    )

    return parser.parse_args()

def _get_save_customer_cone(as_topo, save_file):
    cc_map = get_customer_cone_for_all(as_topo)

    # Write to the file
    INFO = [
        '# Customer cone info.', '# ASes are sorted by their customer cone.',
        '#', '# Format:', '# idx|ASN|customer_cone'
    ]
    with open(save_file, 'w') as f:
        f.writelines(line + '\n' for line in INFO)

        idx = 1
        for asn, customer_cone in cc_map.items():
            f.writelines(f'{idx}|{asn}|{customer_cone}\n')
            idx += 1
    
if __name__ == '__main__':
    args = _parse_args()
    as_topo = load_AS_topology(args.bgp_topo_file)
    _get_save_customer_cone(as_topo, args.save_file)
