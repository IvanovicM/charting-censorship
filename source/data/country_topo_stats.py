import argparse
import os
import sys

from pyvis.network import Network
from tabulate import tabulate

from source.simulation.bgp.countrynet import in_country, get_border_ases, get_mainland
from source.utils import load
from source.utils.utils import country_name, COUNTRIES, check_make_save_file_dir

LATEX_PRINT = False

VIS_NODE_THRESHOLD = 430
SAVE_DIR = 'graphs'
C_NODE_DEFAULT = '#97C2FC'
C_NODE_BORDER = '#73BE73'
C_EDGE_PROV_CUST = '#97C2FC'
C_EDGE_PEER = '#D6332A'

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
    )
    parser.add_argument(
        '--as_org_info_file', default='data/caida/20230101.as-org2info.txt'
    )

    # AS info
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

    # BGP choke potentials for ASN size visualization
    parser.add_argument(
        '--choke_potentials_file',
        default='generated_data/chokepoint_border_mainland_NO_CLEAN/20230101.as-rel2'
    )

    # Other info
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )
    parser.add_argument('--country', '-c', default='CH')

    # Output options
    parser.add_argument('--info', action=argparse.BooleanOptionalAction)
    parser.set_defaults(info=False)
    parser.add_argument('--vis', action=argparse.BooleanOptionalAction)
    parser.set_defaults(vis=False)

    return parser.parse_args()

def _get_choke_potentials(args):
    cpp_f = f'{args.choke_potentials_file}.{args.country}.{args.dataset}.txt'

    try:
        c, total_cnt_outflow, cpp = load.load_choke_potentials(cpp_f)
    except:
        # Either choke potential file not provided, or does not exist.
        # In that case revert to default node size, indicate default with Nones.
        return None, None

    if c != args.country:
        print(f'In file: {c}, but given: {args.country}')
        sys.exit()
    return total_cnt_outflow, cpp

def print_islands_info(as_topo, as_info):

    def _get_country_info(country):
        country_asns = [
            asn for asn in as_topo.keys()
            if in_country(asn, country, as_info)
        ]
        mainland = get_mainland(as_topo, as_info, country)
        border_ases = get_border_ases(as_topo, mainland)
        return len(country_asns), len(mainland), len(border_ases)


    data = list()
    header = ['Country', 'ASes', 'Mainland size', 'Islands size', 'Border ASes']
    for country in COUNTRIES:
        asn_num, mainland_size, border_size = _get_country_info(country)

        mainland_perc = round(100 * mainland_size / asn_num)
        islands_perc = round(100 - mainland_perc)
        border_perc = round(100 * border_size / mainland_size)

        if LATEX_PRINT:
            latex_p = (
                f'{country_name(country)} & {asn_num} & '
                f'{mainland_size} ({mainland_perc}\%) & '
                f'{asn_num-mainland_size} ({islands_perc}\%) & '
                f'{border_size} ({border_perc}\%) \\\\ '
            )
            print(latex_p)
        else:
            data.append([
                country_name(country),
                asn_num,
                f'{mainland_size} (\033[1;32m{mainland_perc}\033[00m %)',
                f'{asn_num-mainland_size} (\033[1;32m{islands_perc}\033[00m %)',
                f'{border_size} (\033[1;32m{border_perc}\033[00m %)',
            ])
    
    if not LATEX_PRINT: print(tabulate(data, headers=header))

def visualize_country_network(args, as_topo, as_info, as_ext, org_ext):
    '''
        Visualized: Only ASes that have at least one customer/peer

        Legend:
            NODE green: border AS
            NODE blue: non-border AS
            EDGE blue: customer --> provider
            EDGE red: peer --- peer
    '''

    total_cnt_outflow, cpp = _get_choke_potentials(args)

    def _choose_visualization_nodes(mainland):
        # Visualize only nodes that have customers or peers
        vis_nodes = set()
        for node in get_border_ases(as_topo, mainland): #mainland:
            rels = as_topo[node]
            if len(rels['customers']) > 0 or len(rels['peers']) > 0:
                vis_nodes.add(node)
        return vis_nodes
    
    def _print_info(html_file_name, mainland, vis_nodes, borders):
        # Legend
        headers = ['Visualized Nodes', 'Nodes legend', 'Edge legend']
        data = list()
        data.append([
            'With at least one customer/peer',
            '\033[92mgreen\033[00m: border AS',
            '\033[34mblue\033[00m: customer --> provider'
        ])
        data.append([
            '',
            '\033[34mblue\033[00m: non-border AS',
            '\033[91mred\033[00m: peer --- peer'
        ])
        print(tabulate(data, headers=headers, tablefmt="fancy_outline"))
        print()

        # Info on country
        headers = ['Country', 'Mainland', 'Visualized Nodes', 'Border ASes', 'Graph File']
        data = [[
            country_name(args.country),
            len(mainland),
            f'{len(vis_nodes)} ({round(100*len(vis_nodes) / len(mainland))} %)',
            f'{len(borders)} ({round(100*len(borders) / len(mainland))} %)',
            f'{os.path.abspath(html_file_name)}'
        ]]
        print(tabulate(data, headers=headers, tablefmt="fancy_outline"))

    def _get_asn_size(asn, border_as):
        DEFAULT_SIZE = 20
        MIN_BORDER_SIZE = 10
        MAX_BORDER_SIZE = 20
        NON_BORDER_SIZE = 5

        if total_cnt_outflow is None or cpp is None:
            return DEFAULT_SIZE
        if not border_as:
            return NON_BORDER_SIZE

        size_scale = cpp[asn] / total_cnt_outflow

        if size_scale > 0.15: print(asn)

        size_shift = size_scale * (MAX_BORDER_SIZE - MIN_BORDER_SIZE)
        return min(MAX_BORDER_SIZE, MIN_BORDER_SIZE + size_shift)

    def _add_node(net, asn, title, border_as=False):
        color = C_NODE_BORDER if border_as else C_NODE_DEFAULT
        asn_size = _get_asn_size(asn, border_as)
        net.add_node(asn, color=color, title=title, size=asn_size)
        return net

    def _add_edge(net, asn_from, asn_to, peers=False):
        color = C_EDGE_PEER if peers else C_EDGE_PROV_CUST
        net.directed = (not peers)
        net.add_edge(asn_from, asn_to, color=color, dashes=peers)
        return net

    # Get nodes to visualize
    mainland = get_mainland(as_topo, as_info, args.country)
    vis_nodes = _choose_visualization_nodes(mainland)
    if len(vis_nodes) > VIS_NODE_THRESHOLD:
        print(f'Too many nodes to visualize ({len(vis_nodes)}).')
        return
    border_ases = set(get_border_ases(as_topo, mainland))

    # Visualize nodes
    net = Network()
    for asn in vis_nodes:
        as_name = as_ext[asn]['as_name']
        org_name = org_ext[as_ext[asn]['org_id']]['org_name']
        title = (
            f'AS {asn}\n'
            f'----- (source: CAIDA) -----\n'
            f'Name: {as_name}\n'
            f'Org: {org_name}'
        )
        net = _add_node(net, asn, title, border_as=asn in border_ases)

    # Visualize edges
    for asn in vis_nodes:
        for cust in as_topo[asn]['customers']:
            if cust not in vis_nodes: continue
            net = _add_edge(net, cust, asn, peers=False)
        
        for peer in as_topo[asn]['peers']:
            if peer not in vis_nodes: continue
            if peer > asn: continue # To avoid duplicates
            net = _add_edge(net, peer, asn, peers=True)

    # Graph options
    net.toggle_physics(True)
    net.show_buttons(filter_=['physics'])
    html_file_name = f'{SAVE_DIR}/countrynet_{args.country}.html'
    check_make_save_file_dir(html_file_name)
    net.show(html_file_name)

    _print_info(html_file_name, mainland, vis_nodes, border_ases)

if __name__ == '__main__':
    args = _parse_args()

    # Data
    as_topo = load.load_AS_topology(args.bgp_topo_file)
    if args.dataset == 'CAIDA':
        as_info = load.load_as_info(args.as_info_caida)
    if args.dataset == 'CYMRU':
        as_info = load.load_as_info(args.as_info_cymru)
    if args.dataset == 'RIPE':
        as_info = load.load_RIPE_geo_countries(args.geo_address_file)
    if args.dataset == 'CAIDA_HYBRID':
        as_info = load.load_as_info(args.as_info_caida_hybrid)

    # Table info
    if args.info:
        print(f'Dataset: \033[32m{args.dataset}\033[00m')
        print_islands_info(as_topo, as_info)
    if args.vis:
        org_ext, as_ext = load.load_ORG_AS_info(args.as_org_info_file)
        visualize_country_network(args, as_topo, as_info, as_ext, org_ext)
