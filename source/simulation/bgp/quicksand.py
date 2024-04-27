import argparse
import copy
import time

from collections import defaultdict, deque
from functools import cmp_to_key
from hashlib import sha256

from source.utils import utils
from source.utils.load import load_AS_topology

def _bgp_simulate_prep(as_topo):
    as_topo_new = copy.deepcopy(as_topo)
    for asn in as_topo.keys():
        as_topo_new[asn]['visited'] = False
        as_topo_new[asn]['preferred_next'] = list()
    return as_topo_new

def _stage_1(as_topo, destination):
    q = deque()
    q.append(destination)
    as_topo[destination]['visited'] = True
    as_topo[destination]['preferred_next'].append({
        'next_hop': None, 'hop_type': None, 'path_length': 0
    })

    routing_tree = deque()
    routing_tree.append(destination)

    while q:
        curr_asn = q.popleft()
        curr_len = as_topo[curr_asn]['preferred_next'][0]['path_length']
        for provider in as_topo[curr_asn]['providers']:
            if not as_topo[provider]['visited']:
                q.append(provider)
                routing_tree.append(provider)
                as_topo[provider]['visited'] = True

            # If the only possible path so far was via a _customer_ at the _same
            #   distance_, then using this customer is also a viable option.
            l_pref_next = as_topo[provider]['preferred_next']
            if (
                len(l_pref_next) == 0 or (
                    l_pref_next[0]['path_length'] == curr_len + 1
                )
            ):
                as_topo[provider]['preferred_next'].append({
                    'next_hop': curr_asn,
                    'hop_type': 'customer',
                    'path_length': curr_len + 1
                })
    
    return as_topo, routing_tree

def _stage_2(as_topo, routing_tree):
    curr_tree = copy.deepcopy(routing_tree)
    for curr_asn in curr_tree:
        curr_len = as_topo[curr_asn]['preferred_next'][0]['path_length']
        for peer in as_topo[curr_asn]['peers']:
            if not as_topo[peer]['visited']:
                routing_tree.append(peer)
                as_topo[peer]['visited'] = True
            
            # If the only possible path so far was via a _peer_ at the _same
            #   distance_, then using this peer is also a viable option.
            l_pref_next = as_topo[peer]['preferred_next']
            if (
                len(l_pref_next) == 0 or (
                    l_pref_next[0]['hop_type'] == 'peer' and
                    l_pref_next[0]['path_length'] == curr_len + 1
                )
            ):
                as_topo[peer]['preferred_next'].append({
                    'next_hop': curr_asn,
                    'hop_type': 'peer',
                    'path_length': curr_len + 1
                })

    return as_topo, routing_tree

def _stage_3(as_topo, routing_tree):
    q = copy.deepcopy(routing_tree)

    while q:
        curr_asn = q.popleft()
        curr_len = as_topo[curr_asn]['preferred_next'][0]['path_length']
        for customer in as_topo[curr_asn]['customers']:
            if not as_topo[customer]['visited']:
                q.append(customer)
                routing_tree.append(customer)
                as_topo[customer]['visited'] = True

            # If the only possible path so far was via a _provider_ at the _same
            #   distance_, then using this provider is also a viable option.
            l_pref_next = as_topo[customer]['preferred_next']
            if (
                len(l_pref_next) == 0 or (
                    l_pref_next[0]['hop_type'] == 'provider' and
                    l_pref_next[0]['path_length'] == curr_len + 1
                )
            ):
                as_topo[customer]['preferred_next'].append({
                    'next_hop': curr_asn,
                    'hop_type': 'provider',
                    'path_length': curr_len + 1
                })
    
    return as_topo, routing_tree

def _sort_with_tiebreak_policies(as_topo, destination):
    def _ranking_cmp(a, b):
        # (LP) customer --> peer --> provider: already satisfied
        # (SP) shortest path: already satisfied
        # (TB) heuristic: hash function
        ha = sha256((asn + a['next_hop']).encode('utf-8')).hexdigest()
        hb = sha256((asn + b['next_hop']).encode('utf-8')).hexdigest()
        if ha < hb: return -1
        return 1

    for asn in as_topo.keys():
        if asn == destination:
            continue
        as_topo[asn]['preferred_next'].sort(key=cmp_to_key(_ranking_cmp))
    return as_topo

def _clean_routing_topo(as_topo):
    clean_topo = defaultdict()
    for asn in as_topo.keys():
        if len(as_topo[asn]['preferred_next']) == 0: continue
        next_hop = as_topo[asn]['preferred_next'][0]['next_hop']
        clean_topo[asn] = next_hop
    return clean_topo

def bgp_simulate(as_topo, destination):
    '''
        Based on the algorithm proposed in the paper: "Modeling on quicksand"
            https://dl.acm.org/doi/10.1145/2096149.2096155 

        Returns dict:
            routing_topo[asn] = <next_hop_asn>
    '''
    as_topo = _bgp_simulate_prep(as_topo)

    as_topo, possible_sources = _stage_1(as_topo, destination)
    as_topo, possible_sources = _stage_2(as_topo, possible_sources)
    as_topo, possible_sources = _stage_3(as_topo, possible_sources)
    as_topo = _sort_with_tiebreak_policies(as_topo, destination)

    return _clean_routing_topo(as_topo)

################################################################################

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
    )
    parser.add_argument(
        '--save_file', default='generated_data/bgp_routes/20230101.as-rel2'
    )
    return parser.parse_args()  

def _save_routing_topo(routing_topo, destination, save_file):
    ROUTING_TOPO_INFO = [
        '# Routing topo', '#', '# Format:', '# ASN|next_hop'
    ]
    file_name = f'{save_file}.D_{destination}.txt'
    with open(file_name, 'w') as f:
        f.writelines(f'# Destination\n{destination}\n')
        
        # Routing topo
        f.writelines(line + '\n' for line in ROUTING_TOPO_INFO)
        for asn, next_hop in routing_topo.items():
            if next_hop is None: continue
            f.writelines(f'{asn}|{next_hop}\n')

def save_routing_topo_all_destinations(args):
    utils.check_make_save_file_dir(args.save_file)
    as_topo = load_AS_topology(args.bgp_topo_file)

    utils.rst_log_counter(counter_max_value=len(as_topo))
    for dest in as_topo.keys():
        utils.log_counter()

        routing_topo = bgp_simulate(as_topo, dest)
        _save_routing_topo(routing_topo, dest, args.save_file) 

if __name__ == '__main__':
    args = _parse_args()
    utils.enable_logger('quicksand', log_dir='logs/quicksand')

    start = time.time()
    save_routing_topo_all_destinations(args)
    end = time.time()
    utils.log_elapsed_time(end-start)