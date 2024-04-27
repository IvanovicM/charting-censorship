import argparse
import json
import math
import sys

from collections import defaultdict
from tabulate import tabulate


from source.simulation.scion.conesize import get_customer_cone_size_core_ISD
from source.simulation.scion.sciongen import get_isd_topos
from source.simulation.scion.scionsim import nodes_within_foreign_reach
from source.utils import load
from source.utils import utils

LATEX_PRINT = False

N_CENSORS = [1, 3, 5, 7, 10, 15, 20]
N_CENSORS_PERC = [1, 2, 5]

DATA_DATE = '20230101.as-rel2'

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
    parser.add_argument(
        '--bgp_crp_results_file',
        default='generated_data/CRP.BGP.results/20230101.as-rel2'
    )
    parser.add_argument(
        '--vpn_crp_results_dir',
        default='generated_data/CRP.VPN.results'
    )
    
    # Arguments
    parser.add_argument('-c', '--country', default='CH')
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )
    parser.add_argument(
        '--vpnmethod', default='MaxMind-AnonG', required=False,
        choices=['MaxMind-AnonG']
    )

    # Output options
    parser.add_argument('--report', action=argparse.BooleanOptionalAction)
    parser.set_defaults(report=True)
    parser.add_argument('--save', action=argparse.BooleanOptionalAction)
    parser.set_defaults(save=False)
    parser.add_argument(
        '--save_file',
        default='results/CRP.ALL.results/20230101.as-rel2'
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

def _latex_table_print(country, country_data, n_list=N_CENSORS):
    latex_p = f'{utils.country_name(country)} &'

    for i in range(len(n_list)):
        for arch_num in range(3):
            value = str( country_data[i * 3 + arch_num + 1] )
            latex_p = latex_p + f' {value} &'
        latex_p = latex_p + '&'

    print(latex_p[:-2] + ' \\\\')

def _bgp_vpn_load(country, bgp_results_file):
    bgpf = f'{bgp_results_file}.{country}.{dataset}.txt'
    c, bgp_censors_by_num, bgp_tot, bgp_res = load.load_bgp_crp_results(bgpf)
    if c != country:
        print(f'Country provided: {country}. In the file found: {c}.')
        sys.exit()
    return bgp_censors_by_num, bgp_tot, bgp_res

def _select_biggest_cone_size_ISD(isd_core_topo, isd_non_core_topo, N):

    def _has_foreign_connection(core_asn, isd_core_topo):
        isd_cores_set = set(isd_core_topo.keys())
        for conn in scion_core_topo[core_asn]['cores']:
            if conn not in isd_cores_set:
                return True
        return False

    isd_cone = get_customer_cone_size_core_ISD(isd_core_topo, isd_non_core_topo)
    
    biggest_cone_cores = set()
    idx = 0
    for core_asn in utils.sort_dict(isd_cone):
        if not _has_foreign_connection(core_asn, isd_core_topo): continue

        # Count only N border ASes
        biggest_cone_cores.add(core_asn)
        idx += 1
        if idx >= N: break

    return biggest_cone_cores

def report_crp_results(args, perc=False, cone_size_scion=True):

    censor_N_list = N_CENSORS_PERC if perc else [1, 5, 10]

    def get_headers():
        headers = ['']
        sufix = '%' if perc else ''
        for N in censor_N_list:
            headers.append(f'N = {N}{sufix}\nBGP')
            headers.append(f'\nVPN')
            headers.append(f'\nSCION')
        return headers

    def get_values_for_N(N):
        # SCION results
        if not cone_size_scion: censors_on_scion = bgp_censors_by_num[N]
        else: censors_on_scion = _select_biggest_cone_size_ISD(
            isd_core_topo, isd_non_core_topo, N
        )

        scion_reach = len( nodes_within_foreign_reach(
            scion_core_topo, isd_core_topo, isd_non_core_topo, as_info,
            country, censors=censors_on_scion
        ))
        
        # Get resulting values
        a = round( math.floor(100 * bgp_results[N] / bgp_results[0]) / 100, 2)
        b = round( math.floor(100 * vpn_results[N] / vpn_results[0]) / 100, 2)
        c = round( math.floor(100 * scion_reach / scion_all_reach) / 100, 2)
        values = [a, b, c]

        # Compare values
        max_idx = len(values) - 1 - values[::-1].index(max(values))
        if not LATEX_PRINT:
            values[max_idx] = f'\033[92m{values[max_idx]}\033[00m'
        else:
            values[max_idx] = '\\textbf{' + str(values[max_idx]) + '}'

        return values

    # Prepare data and headers
    data = list()
    headers = get_headers()

    # Populate the data
    for country in utils.COUNTRIES:
        # BGP / VPN results
        try:
            bgp_censors_by_num, tot_pot_censors, bgp_results = _bgp_vpn_load(
                country, args.bgp_crp_results_file
            )
        except:
            continue

        # VPN
        try:
            _, _, vpn_results = _bgp_vpn_load(
                country,
                f'{args.vpn_crp_results_dir}.{args.vpnmethod}/{DATA_DATE}'
            )
        except:
            vpn_results = defaultdict(int)
            vpn_results[0] = 1

        # SCION ISD
        isd_core_topo, isd_non_core_topo = get_isd_topos(
            scion_core_topo, as_topo, cones, as_info, country
        )
        scion_all_reach = len( nodes_within_foreign_reach(
            scion_core_topo, isd_core_topo, isd_non_core_topo, as_info, country,
            censors=set()
        ))

        # Results
        country_data = [utils.country_name(country)]
        for N in censor_N_list:
            if perc: N = math.ceil(N/100 * tot_pot_censors)

            values = get_values_for_N(N)
            for res in values:
                country_data.append(res)
            
        if LATEX_PRINT: _latex_table_print(country, country_data)
        data.append(country_data)

    # Print the data
    if not LATEX_PRINT: print(tabulate(data, headers=headers))
    return data

def get_crp_results(args, perc=False, cone_size_scion=True):

    censor_N_list = N_CENSORS_PERC if perc else N_CENSORS

    def get_values_for_N(N):
        # SCION results
        if not cone_size_scion: censors_on_scion = bgp_censors_by_num[N]
        else: censors_on_scion = _select_biggest_cone_size_ISD(
            isd_core_topo, isd_non_core_topo, N
        )

        scion_reach = len( nodes_within_foreign_reach(
            scion_core_topo, isd_core_topo, isd_non_core_topo, as_info,
            country, censors=censors_on_scion
        ))
        
        # Get resulting values
        a = round( math.floor(100 * bgp_results[N] / bgp_results[0]) / 100, 2)
        b = round( math.floor(100 * vpn_results[N] / vpn_results[0]) / 100, 2)
        c = round( math.floor(100 * scion_reach / scion_all_reach) / 100, 2)

        return a, b, c

    # Prepare data
    data = defaultdict(lambda: defaultdict(lambda: defaultdict()))

    # Populate the data
    for country in utils.COUNTRIES:
        # BGP results
        try:
            bgp_censors_by_num, tot_pot_censors, bgp_results = _bgp_vpn_load(
                country, args.bgp_crp_results_file
            )
        except:
            continue

        # VPN results
        try:
            _, _, vpn_results = _bgp_vpn_load(
                country,
                f'{args.vpn_crp_results_dir}.{args.vpnmethod}/{DATA_DATE}'
            )
        except:
            continue

        # SCION ISD results
        isd_core_topo, isd_non_core_topo = get_isd_topos(
            scion_core_topo, as_topo, cones, as_info, country
        )
        scion_all_reach = len( nodes_within_foreign_reach(
            scion_core_topo, isd_core_topo, isd_non_core_topo, as_info, country,
            censors=set()
        ))

        # Results
        for N in censor_N_list:
            if perc: N_abs = math.ceil(N/100 * tot_pot_censors)
            else: N_abs = N

            bgp_res, vpn_res, scion_res = get_values_for_N(N_abs)
            data[country]['BGP'][N] = bgp_res
            data[country]['VPN'][N] = vpn_res
            data[country]['SCION'][N] = scion_res
            
    data['metadata'] = {'perc': perc, 'cone_size_scion': cone_size_scion}
    return data

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)

    if args.report:
        utils.print_divider()
        print('~~~ \033[32mNational Censorship Resilience Potential\033[00m ~~~')
        print(f'Dataset: \033[32m{dataset}\033[00m')
        report_crp_results(args, perc=False)
        utils.print_divider('.')
    if args.save:
        utils.check_make_save_file_dir(args.save_file)

        data = get_crp_results(args, perc=False, cone_size_scion=True)
        file_name = f'{args.save_file}.{args.dataset}.json'
        with open(file_name, 'w') as f:
            json.dump(data, f)


