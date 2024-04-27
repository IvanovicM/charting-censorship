import argparse

from collections import defaultdict
from statistics import median

from source.simulation.bgp.countrynet import get_mainland, in_country
from source.utils.load import load_customer_cone, load_AS_topology
from source.utils.utils import sort_dict

# ==============================================================================
# ================================  CORE  ======================================
# ==============================================================================

def select_scion_cores(
    cones, as_topo, N=2000, remo=True, with_rels=False
):
    
    def _get_with_highest_cone():
        nodes_sorted = {
            k: v
            for k, v in sorted(cones.items(), key=lambda x: x[1], reverse=True)
        }
        asn_by_customer_cone = list(nodes_sorted.keys())
        
        # Select _at most_ N of them
        deg = cones[asn_by_customer_cone[N - 1]]
        if deg != cones[asn_by_customer_cone[N]]:
            return asn_by_customer_cone[:N]

        below_N_cnt = len([
            asn for idx, asn in enumerate(asn_by_customer_cone)
            if cones[asn] == deg and idx < N
        ])
        return asn_by_customer_cone[:(N - below_N_cnt)]
    
    def _get_scion_core_topo_with_rels(cores):
        scion_core_topo = defaultdict(lambda: defaultdict(list))
        cores_set = set(cores)
        for core_as in cores:
            scion_core_topo[core_as]['providers'] = list()
            scion_core_topo[core_as]['customers'] = list()
            scion_core_topo[core_as]['peers'] = list()

            for prov in as_topo[core_as]['providers']:
                if prov in cores_set:
                    scion_core_topo[core_as]['providers'].append(prov)
            for cust in as_topo[core_as]['customers']:
                if cust in cores_set:
                    scion_core_topo[core_as]['customers'].append(cust)
            for peer in as_topo[core_as]['peers']:
                if peer in cores_set:
                    scion_core_topo[core_as]['peers'].append(peer)
        return scion_core_topo
    
    def _get_scion_core_topo_no_rels(cores):
        scion_core_topo = defaultdict(lambda: defaultdict(list))
        cores_set = set(cores)
        for core_as in cores:
            scion_core_topo[core_as]['cores'] = list()

            for prov in as_topo[core_as]['providers']:
                if prov in cores_set:
                    scion_core_topo[core_as]['cores'].append(prov)
            for cust in as_topo[core_as]['customers']:
                if cust in cores_set:
                    scion_core_topo[core_as]['cores'].append(cust)
            for peer in as_topo[core_as]['peers']:
                if peer in cores_set:
                    scion_core_topo[core_as]['cores'].append(peer)
        return scion_core_topo
    
    def _get_core_topo(cores):
        if with_rels:
            return _get_scion_core_topo_with_rels(cores)
        return _get_scion_core_topo_no_rels(cores)
    
    cores = _get_with_highest_cone()
    cores = [x for x in cores if x not in set(['64302', '306'])]
    scion_core_topo = _get_core_topo(cores)
    return scion_core_topo

# ==============================================================================
# ================================  ISD  =======================================
# ==============================================================================

def select_isd_cores_of_country(
    scion_core_topo, cones, as_info, country, max_cores=2000,
    connect=False, with_rels=False
):
    
    def _select_isd_cores():
        country_cones = [
            (k, v) for k, v in cones.items()
            if k in scion_core_topo.keys() and in_country(k, country, as_info)
        ]

        # Or only a couple, with highest customer cone size?
        country_cones = sorted(country_cones, key=lambda x: x[1], reverse=True)
        select_num = min(max_cores, len(country_cones))
        return [asn for (asn, _) in country_cones[:select_num]]
    
    def _get_isd_core_topo_with_rels(isd_cores):
        isd_core_topo = defaultdict(lambda: defaultdict(list))
        isd_cores_set = set(isd_cores)
        for isd_core in isd_cores:
            isd_core_topo[isd_core]['providers'] = list()
            isd_core_topo[isd_core]['customers'] = list()
            isd_core_topo[isd_core]['peers'] = list()

            for prov in scion_core_topo[isd_core]['providers']:
                if prov in isd_cores_set:
                    isd_core_topo[isd_core]['providers'].append(prov)
            for cust in scion_core_topo[isd_core]['customers']:
                if cust in isd_cores_set:
                    isd_core_topo[isd_core]['customers'].append(cust)
            for peer in scion_core_topo[isd_core]['peers']:
                if peer in isd_cores_set:
                    isd_core_topo[isd_core]['peers'].append(peer)
        return isd_core_topo
    
    def _get_isd_core_topo_no_rels(isd_cores):
        isd_core_topo = defaultdict(lambda: defaultdict(list))
        isd_cores_set = set(isd_cores)
        for isd_core in isd_cores:
            isd_core_topo[isd_core]['cores'] = list()

            for conn in scion_core_topo[isd_core]['cores']:
                if conn in isd_cores_set:
                    isd_core_topo[isd_core]['cores'].append(conn)
        return isd_core_topo
    
    def _get_isd_core_topo(isd_cores):
        if with_rels:
            return _get_isd_core_topo_with_rels(isd_cores)
        return _get_isd_core_topo_no_rels(isd_cores)

    def _connection_cnt(isd_core_topo, asn):
        rels = isd_core_topo[asn]
        if with_rels:
            return len(rels['peers'] + rels['customers'] + rels['providers'])
        return len(rels['cores'])

    def _add_missing_link(isd_core_topo, asn1, asn2):
        if with_rels:
            isd_core_topo[asn1]['peers'] = asn2
            isd_core_topo[asn2]['peers'] = asn1
        else:
            isd_core_topo[asn1]['cores'] = asn2
            isd_core_topo[asn2]['cores'] = asn1
        return isd_core_topo

    def _add_missing_core_links(isd_core_topo):
        # Median connection + ASNs with max connections in the ISD
        asn2conn_cnt = sort_dict({
            asn: _connection_cnt(isd_core_topo, asn)
            for asn in isd_core_topo.keys()
        })
        median_connections = median([
            asn2conn_cnt[asn] for asn in isd_core_topo.keys()
            if asn2conn_cnt[asn] > 0
        ])
        max_connected = list(asn2conn_cnt.keys())[:median_connections]

        # ASes with no connection + to be connected
        wno_connection = [
            asn for asn in isd_core_topo.keys() if asn2conn_cnt[asn] == 0
        ]
        for asn1 in max_connected:
            for asn2 in wno_connection:
                isd_core_topo = _add_missing_link(isd_core_topo, asn1, asn2)
                
        return isd_core_topo

    isd_cores = _select_isd_cores()
    isd_core_topo = _get_isd_core_topo(isd_cores)

    # if connect: isd_core_topo = _add_missing_core_links(isd_core_topo)
    
    return isd_core_topo

def select_isd_non_cores_of_country(
    isd_core_topo, as_topo, as_info, country
):

    def _get_isd_non_cores():
        mainland = get_mainland(as_topo, as_info, country)

        isd_cores_set = set(isd_core_topo.keys())
        isd_non_cores = [asn for asn in mainland if asn not in isd_cores_set]
        return isd_non_cores

    def _get_isd_non_core_topo(isd_non_cores):
        isd_non_core_topo = defaultdict(lambda: defaultdict(list))
        isd_non_cores_set = set(isd_non_cores)
        isd_cores_set = set(isd_core_topo.keys())
        isd_all_set = isd_non_cores_set.union(isd_cores_set)

        # Process non-cores
        for isd_non_core in isd_non_cores:
            isd_non_core_topo[isd_non_core]['providers'] = list()
            isd_non_core_topo[isd_non_core]['customers'] = list()
            isd_non_core_topo[isd_non_core]['peers'] = list()

            for prov in as_topo[isd_non_core]['providers']:
                if prov in isd_all_set:
                    isd_non_core_topo[isd_non_core]['providers'].append(prov)
            
            for cust in as_topo[isd_non_core]['customers']:
                if cust in isd_non_cores_set:
                    isd_non_core_topo[isd_non_core]['customers'].append(cust)
                if cust in isd_cores_set:
                    isd_non_core_topo[isd_non_core]['peers'].append(cust)
            
            for peer in as_topo[isd_non_core]['peers']:
                if peer in isd_all_set:
                    isd_non_core_topo[isd_non_core]['peers'].append(peer)

        # Process cores
        for isd_core in isd_core_topo.keys():
            isd_non_core_topo[isd_core]['providers'] = list()
            isd_non_core_topo[isd_core]['customers'] = list()
            isd_non_core_topo[isd_core]['peers'] = list()

            for prov in as_topo[isd_core]['providers']:
                if prov in isd_non_cores_set:
                    isd_non_core_topo[isd_core]['peers'].append(prov)
                    #isd_non_core_topo[isd_core]['providers'].append(prov)
            
            for cust in as_topo[isd_core]['customers']:
                if cust in isd_non_cores_set:
                    isd_non_core_topo[isd_core]['customers'].append(cust)
            
            for peer in as_topo[isd_core]['peers']:
                if peer in isd_non_cores_set:
                    isd_non_core_topo[isd_core]['peers'].append(peer)

        return isd_non_core_topo
    
    isd_non_cores = _get_isd_non_cores()
    isd_non_core_topo = _get_isd_non_core_topo(isd_non_cores)
    return isd_non_core_topo

def get_isd_topos(
    scion_core_topo, as_topo, cones, as_info, country,
    use_all_cores=True
):
    isd_core_topo = select_isd_cores_of_country(
        scion_core_topo, cones, as_info, country
    )
    isd_non_core_topo = select_isd_non_cores_of_country(
        isd_core_topo, as_topo, as_info, country
    )

    return isd_core_topo, isd_non_core_topo

################################################################################

def _save_scion_core_topo(scion_core_topo, save_file):
    INFO = [
        '# SCION core AS topology', '#', '# Format:',
        '# provider_ASN|customer_ASN|-1', '# peer_ASN1|peer_ASN2|0'
    ]
    with open(save_file, 'w') as f:
        f.writelines(line + '\n' for line in INFO)
        peer_links = set() # to avoid duplicates

        for asn in scion_core_topo.keys():
            for cust in scion_core_topo[asn]['customers']:
                f.write(f'{asn}|{cust}|-1\n')

            for peer in scion_core_topo[asn]['peers']:
                if f'{peer}_{asn}' in peer_links: continue
                peer_links.add(f'{asn}_{peer}')
                f.write(f'{asn}|{peer}|0\n')

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
    )
    parser.add_argument(
        '--customer_cone_file',
        default='data/scion/20230101.customer-cone-size.txt'
    )
    parser.add_argument(
        '--save_file',
        default='data/scion/20230101.SCION_core_topo.txt'
    )
    parser.add_argument('-N', type=int, default=2000)

    return parser.parse_args()
    
if __name__ == '__main__':
    args = _parse_args()
    
    N = args.N
    cones = load_customer_cone(args.customer_cone_file)
    as_topo = load_AS_topology(args.bgp_topo_file)

    scion_core_topo = select_scion_cores(cones, as_topo, N=N, with_rels=True)
    _save_scion_core_topo(scion_core_topo, args.save_file)
