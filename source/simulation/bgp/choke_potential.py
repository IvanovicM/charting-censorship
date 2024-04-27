import argparse
import logging
import os
import time

from collections import defaultdict

from source.utils import utils
from source.utils import load
from source.simulation.bgp.countrynet import get_border_ases, get_mainland

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
        '--routing_file_root',
        default='generated_data/bgp_routes/20230101.as-rel2'
    )
    parser.add_argument(
        '--save_file',
        default='generated_data/chokepoint_border_mainland_NO_CLEAN/20230101.as-rel2'
    )
    parser.add_argument('-c', '--country')
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )

    return parser.parse_args()

def _set_global_vars(args):

    global country, dataset, as_topo, mainland
    country = args.country
    dataset = args.dataset

    as_topo = load.load_AS_topology(args.bgp_topo_file)

    if dataset == 'CAIDA_HYBRID':
        as_info = load.load_as_info(args.as_info_caida_hybrid)
    
    mainland = get_mainland(as_topo, as_info, country)

def _is_in_mainland(asn):
    return asn in mainland

def _get_reverse_routing_topo(routing_topo, destination):
    reverse_topo = defaultdict(list)
    for source, next_hop in routing_topo.items():
        if source == destination: continue
        if next_hop is None: continue

        reverse_topo[next_hop].append(source)
    
    return reverse_topo

def _routing_topo_of_destination(destination, routing_file_root):
    # Is the destination at the right side of the border?
    if _is_in_mainland(destination):
        return None

    # Does this file exist, and contain right information?
    destination_routing_file = f'{routing_file_root}.D_{destination}.txt'
    if not os.path.isfile(destination_routing_file):
        logging.warning(f'File not found: {destination_routing_file}')
        return None
    d, routing_topo = load.load_routing_topo(destination_routing_file)
    if d != destination: 
        logging.warning(
            f'File {destination_routing_file} contains routing info for '
            'destination {d}, although it should contain routing info for '
            'destination {destination}.'
        )
        return None

    return routing_topo

def _sub_tree_cnt(asn2sub_tree_cnt, tree, root):
    sub_tree_sz = 0
    if _is_in_mainland(root): sub_tree_sz += 1

    if root not in tree.keys():
        asn2sub_tree_cnt[root] = sub_tree_sz
        return asn2sub_tree_cnt
    
    for child in tree[root]:
        asn2sub_tree_cnt = _sub_tree_cnt(asn2sub_tree_cnt, tree, child)
        sub_tree_sz += asn2sub_tree_cnt[child]

    asn2sub_tree_cnt[root] = sub_tree_sz
    return asn2sub_tree_cnt

def _update_cp_intercepted(
    cp_intercepted, asn2sub_tree_cnt, border_ases, routing_topo
):
    '''
        For a border AS its chokepoint potential will be updated only if its
            next hope---for the given routing tree---is outside the country.
    '''
    for border_as in border_ases:
        if border_as not in routing_topo.keys(): continue
        next_hop = routing_topo[border_as]
        if not _is_in_mainland(next_hop):
            cp_intercepted[border_as] += asn2sub_tree_cnt[border_as]
    return cp_intercepted

def _update_chokepoint_potentials_by_destination(
    border_ases, cp_intercepted, path_cnt, destination, routing_file_root
):
    # Routing & reverse topo
    routing_topo = _routing_topo_of_destination(destination, routing_file_root) 
    if routing_topo is None: return path_cnt, cp_intercepted
    reverse_topo = _get_reverse_routing_topo(routing_topo, destination)

    # Total paths
    path_cnt += len([s for s in routing_topo.keys() if _is_in_mainland(s)])

    # Subtree size counts
    asn2sub_tree_cnt = defaultdict(int)
    asn2sub_tree_cnt = _sub_tree_cnt(
        asn2sub_tree_cnt, reverse_topo, destination
    )

    # Calc and update chokepoint potentials based on this _clean_ routing topo.
    cp_intercepted = _update_cp_intercepted(
        cp_intercepted, asn2sub_tree_cnt, border_ases, routing_topo
    )
    return path_cnt, cp_intercepted

def _chokepoint_potentials(border_ases, routing_file_root):
    cp_intercepted = defaultdict(int)
    path_cnt = 0

    utils.rst_log_counter(counter_max_value=len(as_topo))
    for destination in as_topo.keys():
        utils.log_counter()

        path_cnt, cp_intercepted = _update_chokepoint_potentials_by_destination(
            border_ases, cp_intercepted, path_cnt, destination,
            routing_file_root
        )
    return path_cnt, cp_intercepted

def _calc_save_chokepoint_potentials(routing_file_root, save_file):
    border_ases = get_border_ases(as_topo, mainland)
    path_cnt, cp_potentials = _chokepoint_potentials(
        border_ases, routing_file_root
    )

    # Save to a file
    utils.check_make_save_file_dir(args.save_file)
    INITIAL_INFO = [
        '# Country info; focus on the mainland only', '#',
        '# Format:', '# Country|total_path_cnt'
    ]
    CHOKEPOINT_INFO = [
        '# Chokepoint potentials', '#', '# Format:',
        '# Border_ASN|intercepted_outflow_cnt'
    ]
    file_name = f'{save_file}.{country}.{dataset}.txt'
    with open(file_name, 'w') as f:
        # Info dump
        f.writelines(line + '\n' for line in INITIAL_INFO)
        f.writelines(f'{country}|{path_cnt}\n')
        f.writelines(line + '\n' for line in CHOKEPOINT_INFO)

        # Save outflow + inflow data
        for border_asn in border_ases:
            outflow_cnt = cp_potentials[border_asn]
            f.writelines(f'{border_asn}|{outflow_cnt}\n')

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)
    utils.enable_logger(
        f'chokepoint_border.mainland.{country}',
        log_dir=f'logs/chokepoint_border_mainland.NO_CLEAN.{dataset}'
    )

    start = time.time()   
    _calc_save_chokepoint_potentials(args.routing_file_root, args.save_file)
    end = time.time()
    utils.log_elapsed_time(end-start)
