import argparse
import logging
import os
import random
import time

from source.utils import utils
from source.utils import load

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
        default='generated_data/BGP.global.reach.results/20230101.as-rel2'
    )
    parser.add_argument('--hegemons', default='United States')
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )

    return parser.parse_args()

def _set_global_vars(args):
    global country
    global dataset, as_topo, as_info, mainland
    dataset = args.dataset

    as_topo = load.load_AS_topology(args.bgp_topo_file)

    if dataset == 'CAIDA_HYBRID':
        as_info = load.load_as_info(args.as_info_caida_hybrid)
        for asn, list_countries in as_info.items():
            if len(list_countries) > 1: as_info[asn] = list(['-'])

def _country_origin(asn):
    return as_info[asn][0]

def _routing_topo_of_destination(destination, routing_file_root):
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

def _is_intercepted(source, destination, routing_topo, hegemons):
    curr_node = source
    while curr_node != destination:
        if _country_origin(curr_node) in hegemons: return True
        curr_node = routing_topo[curr_node]
    return False

def _could_reach(source, destination, hegemons, dest_routing_topo):
    if _country_origin(source) in hegemons or _country_origin(destination) in hegemons: return False
    if len(hegemons) == 0: return source in dest_routing_topo.keys()
    if source not in dest_routing_topo.keys(): return False
    return not _is_intercepted(source, destination, dest_routing_topo, hegemons)

def _reachability_by_dest(hegemons, destination, routing_file_root):

    def _not_intercepted(routing_topo):
        not_intercepted = 0
        paths_to_dest = 0
        for source in routing_topo.keys():
            if source == destination: continue
            if _country_origin(source) in hegemons: continue

            paths_to_dest += 1
            if _could_reach(source, destination, hegemons, routing_topo):
                not_intercepted += 1
        return paths_to_dest, not_intercepted

    # Destination shouldn't be one of hegemons
    if _country_origin(destination) in hegemons: return 0, 0
    
    # Routing topo
    routing_topo = _routing_topo_of_destination(destination, routing_file_root) 
    if routing_topo is None: return 0, 0

    # Updates
    paths_to_dest, not_intercepted_to_dest = _not_intercepted(routing_topo)
    return paths_to_dest, not_intercepted_to_dest

def _global_reach_potentials(hegemons, routing_file_root):
    total_path_cnt = 0
    total_not_intercepted = 0

    all_asns = list(as_topo.keys())
    random.shuffle(all_asns)

    utils.rst_log_counter(counter_max_value=len(as_topo))
    for destination in all_asns:
        utils.log_counter()

        paths_to_dest, not_intercepted_to_dest = _reachability_by_dest(
            hegemons, destination, routing_file_root
        )
        total_path_cnt += paths_to_dest
        total_not_intercepted += not_intercepted_to_dest

    return total_path_cnt, total_not_intercepted

def _calc_save_global_reach_potentials(rfr, hegemon_group_name, save_file):
    hegs = set(utils.HEG_GROUPS[hegemon_group_name])
    total_paths, free_paths = _global_reach_potentials(hegs, rfr)

    # Save to a file
    utils.check_make_save_file_dir(args.save_file)
    INITIAL_INFO = [
        '# Global reachability', '#','# Format:',
        '# hegemon_group_name|country_1, ..., country_N',
        '# hegemon_group_name|total_path_cnt|not_intercepted_cnt'
    ]
    file_name = f'{save_file}.{args.hegemons.replace(" ", "-")}.{dataset}.txt'
    with open(file_name, 'w') as f:
        f.writelines(line + '\n' for line in INITIAL_INFO)
        f.writelines(f'{hegemon_group_name}|{",".join(hegs)}\n')
        f.writelines(f'{hegemon_group_name}|{total_paths}|{free_paths}\n')

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)
    utils.enable_logger(
        f'global.reachability.{args.hegemons.replace(" ", "-")}',
        log_dir=f'logs/BGP.global.reach.{dataset}'
    )

    start = time.time()   
    _calc_save_global_reach_potentials(
        args.routing_file_root, args.hegemons, args.save_file
    )
    end = time.time()
    utils.log_elapsed_time(end - start)
