import argparse
from collections import defaultdict
import math
import sys

from tabulate import tabulate

from source.simulation.scion.conesize import get_customer_cone_size_core_ISD
from source.simulation.scion.sciongen import get_isd_topos
from source.utils import load
from source.utils.utils import pretty_print, sort_dict

N_CENSORS = [1, 5, 10]
N_CENSORS_PERC = [1, 2, 5]

def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
    )

    parser.add_argument(
        '--as_info_caida', default='data/caida/20230101.as-info.txt'
    )
    parser.add_argument(
        '--as_info_cymru', default='data/cymru/cymru_as_data.txt'
    )
    parser.add_argument(
        '--as_info_caida_hybrid', default='data/ripe/as-info-tier1-hybrid.txt'
    )
    parser.add_argument(
        '--geo_address_file',
        default='data/ripe/20230315.asns-geo_address_space.txt'
    )

    parser.add_argument(
        '--customer_cone_file',
        default='data/scion/20230101.customer-cone-size.txt'
    )
    parser.add_argument(
        '--SCION_core_topo',
        default='data/scion/20230101.SCION_core_topo.txt'
    )
    
    # Arguments
    parser.add_argument('-c', '--country', default='CH')
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )

    return parser.parse_args()

def _set_global_vars(args):
    global dataset, as_topo
    dataset = args.dataset

    global as_topo, as_info
    as_topo = load.load_AS_topology(args.bgp_topo_file)

    if dataset == 'CAIDA_HYBRID':
        as_info = load.load_as_info(args.as_info_caida_hybrid)

    global cones, scion_core_topo
    cones = load.load_customer_cone(args.customer_cone_file)
    scion_core_topo = load.load_SCION_core_topo_no_rels(args.SCION_core_topo)

def select_biggest_cone_size(country, N):

    def _has_foreign_connection(core_asn, isd_core_topo):
        isd_cores_set = set(isd_core_topo.keys())
        for conn in scion_core_topo[core_asn]['cores']:
            if conn not in isd_cores_set:
                return True
        return False

    isd_core_topo, isd_non_core_topo = get_isd_topos(
        scion_core_topo, as_topo, cones, as_info, country
    )
    isd_cone = get_customer_cone_size_core_ISD(isd_core_topo, isd_non_core_topo)
    
    biggest_cone_cores = set()
    idx = 0
    for core_asn in sort_dict(isd_cone):
        if not _has_foreign_connection(core_asn, isd_core_topo): continue

        # Count only N border ASes
        biggest_cone_cores.add(core_asn)
        idx += 1
        if idx >= N: break

    return biggest_cone_cores

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)

    select_biggest_cone_size(args.country, N=5)
