import argparse
import sys

from tabulate import tabulate

from source.utils import load
from source.utils import utils

LATEX_PRINT = False

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_global_reach_file',
        default='generated_data/BGP.global.reach.results/20230101.as-rel2'
    )
    parser.add_argument(
        '--vpn_global_reach_file',
        default='generated_data/VPN.global.reach.results/20230101.as-rel2'
    )
    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )

    return parser.parse_args()

def _load_global_reach(heg_group, file_name, dataset):
    fn = f'{file_name}.{heg_group.replace(" ", "-")}.{dataset}.txt'

    try:
        h, countries, total_path_cnt, int_free = load.load_global_reach_info(fn)
    except:
        return 1, 0, list()

    if h != heg_group:
        sys.exit(f'File error! In file: {h}, but given: {heg_group}')

    return total_path_cnt, int_free, countries

def _latex_table_print(heg_data):
    latex_p = ' & '.join(f'{c}' for c in heg_data)
    latex_p += ' \\\\'
    print(latex_p)

def report_grp_results(args):
    # Prepare data and headers
    data = list()
    headers = ['', 'BGP', 'VPN']

    # Populate the data
    for heg_group in utils.HEG_GROUPS.keys():
        heg_data = list([heg_group])

        # ===== BGP =====
        total_path_cnt, int_free, _ = _load_global_reach(
            heg_group, args.bgp_global_reach_file, args.dataset
        )
        heg_group_res = round(int_free / total_path_cnt, 2)
        heg_data.append(heg_group_res)

        # ===== VPN =====
        total_path_cnt, int_free, _ = _load_global_reach(
            heg_group, args.vpn_global_reach_file, args.dataset
        )
        heg_group_res = round(int_free / total_path_cnt, 2)
        heg_data.append(heg_group_res)

        # ===============

        if LATEX_PRINT: _latex_table_print(heg_data)
        data.append(heg_data)

    # Print the data
    if not LATEX_PRINT: print(tabulate(data, headers=headers))

if __name__ == '__main__':
    args = _parse_args()

    utils.print_divider()
    print('~~~ \033[32mGlobal (Internet) Reachability Potential\033[00m ~~~')
    print(f'Dataset: \033[32m{args.dataset}\033[00m')
    report_grp_results(args)
    utils.print_divider()
