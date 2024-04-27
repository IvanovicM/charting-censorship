import argparse
import logging
import math
import os
import random
import sys
import time

from collections import defaultdict

from source.utils import utils
from source.utils import load
from source.simulation.bgp.countrynet import get_mainland

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--routing_file_root',
        default='generated_data/bgp_routes/20230101.as-rel2'
    )
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
        '--choke_potentials_file',
        default='generated_data/chokepoint_border_mainland/20230101.as-rel2'
    )
    parser.add_argument(
        '--save_file',
        default='generated_data/CRP.BGP.add.results/20230101.as-rel2'
    )
    parser.add_argument('-c', '--country', default='CH')
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )

    parser.add_argument('--Ns', nargs="+", type=int, required=True)

    return parser.parse_args()

def _get_potential_censors(choke_potentials_file):
    cpp_f = f'{choke_potentials_file}.{country}.{dataset}.txt'
    c, _, cpp = load.load_choke_potentials(cpp_f)
    if c != country:
        logging.warning(f'In file: {c}, but given: {country}')
        sys.exit()
    sorted_cpp = utils.sort_dict(cpp)
    return list(sorted_cpp.keys())

def _create_censors_by_num(choke_potentials_file):
    global pot_censors_num

    potential_censors = _get_potential_censors(choke_potentials_file)
    pot_censors_num = len(potential_censors)
    censors_by_num = defaultdict(set)

    for N in N_CENSORS:
        if N > pot_censors_num: continue

        censor_num = min(pot_censors_num, N)
        top_censors = potential_censors[:censor_num]
        censors_by_num[N] = set(top_censors)
    
    return censors_by_num

def _set_global_vars(args):

    global country, dataset, as_topo, mainland
    country = args.country
    dataset = args.dataset

    as_topo = load.load_AS_topology(args.bgp_topo_file)
    
    if dataset == 'CAIDA_HYBRID':
        as_info = load.load_as_info(args.as_info_caida_hybrid)
    mainland = get_mainland(as_topo, as_info, country)

    global non_mainland
    non_mainland = [
        asn for asn in as_topo.keys() if not asn in mainland
    ]
    random.shuffle(non_mainland)

    global routing_file_root
    routing_file_root = args.routing_file_root

    global censors_by_num, N_CENSORS
    N_CENSORS = args.Ns
    censors_by_num = _create_censors_by_num(args.choke_potentials_file)

def _routing_topo_of_destination(destination):
    destination_routing_file = f'{routing_file_root}.D_{destination}.txt'
    if not os.path.isfile(destination_routing_file):
        logging.warning(f'File not found: {destination_routing_file}')
        sys.exit()
    d, routing_topo = load.load_routing_topo(destination_routing_file)
    if d != destination: 
        logging.warning(
            f'File {destination_routing_file} contains routing info for '
            'destination {d}, although it should contain routing info for '
            'destination {destination}.'
        )
        sys.exit()

    return routing_topo

def _is_censored(source, destination, routing_topo, censors):
    curr_node = source
    while curr_node != destination:
        if curr_node in censors: return True
        curr_node = routing_topo[curr_node]
    return False

def _could_reach(source, destination, censors, dest_routing_topo):
    if source in censors or destination in censors: return False
    if len(censors) == 0: return source in dest_routing_topo.keys()
    if source not in dest_routing_topo.keys(): return False
    return not _is_censored(source, destination, dest_routing_topo, censors)

def _get_bgp_results():
    data = defaultdict(int)

    utils.rst_log_counter(counter_max_value=len(non_mainland))
    for destination in non_mainland:
        utils.log_counter()
        dest_routing_topo = _routing_topo_of_destination(destination)

        if dest_routing_topo is None: continue

        for source in mainland:
            for N in N_CENSORS:
                censors = censors_by_num[N]
                reached = _could_reach(
                    source, destination, censors, dest_routing_topo
                )
                if reached:
                    data[N] += 1

    return data

def _calc_save_bgp_results(save_file, info_plus):
    data = _get_bgp_results()

    # Save to a file
    utils.check_make_save_file_dir(args.save_file)
    INITIAL_INFO = ['# Country info', '#', '# Format:', '# <Country>']
    CENSORS_INFO = [
        '# Info about censors', '#', '# Format:',
        '# <total_potential_censor_num>',
        '# censors_num_N|censor_1,censor_2,...,censor_N'
    ]
    BGP_METRIC_INFO = [
        '# Chokepoint potentials', '#', '# Format:',
        '# censor_num|total_reach_outflow_path'
    ]
    file_name = f'{save_file}.{country}.{info_plus}.{dataset}.txt'
    with open(file_name, 'w') as f:
        # Info dump
        f.writelines(line + '\n' for line in INITIAL_INFO)
        f.writelines(f'{country}\n')
        
        # Save data about censors
        f.writelines(line + '\n' for line in CENSORS_INFO)
        f.writelines(f'{pot_censors_num}\n')
        for N, cens in censors_by_num.items():
            cens_str = ','.join(cens)
            f.writelines(f'{N}|{cens_str}\n')

        # Save data for all N
        f.writelines(line + '\n' for line in BGP_METRIC_INFO)
        for N, reach in data.items():
            f.writelines(f'{N}|{reach}\n')

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)

    info_plus = '_'.join([str(n) for n in N_CENSORS])

    utils.enable_logger(
        f'CRP.BGP.results.{country}.{info_plus}', log_dir=f'logs/CRP.BGP.add.{dataset}'
    )

    start = time.time()   
    _calc_save_bgp_results(args.save_file, info_plus)
    end = time.time()
    utils.log_elapsed_time(end-start)
