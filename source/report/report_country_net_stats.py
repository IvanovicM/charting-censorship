import argparse

from tabulate import tabulate

from source.simulation.bgp.countrynet import get_border_ases, get_mainland
from source.simulation.scion.sciongen import get_isd_topos
from source.utils import load
from source.utils.utils import country_name, COUNTRIES

LATEX_PRINT = False

def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bgp_topo_file', default='data/caida/20230101.as-rel2.txt'
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

    # SCION info
    parser.add_argument(
        '--customer_cone_file',
        default='data/scion/20230101.customer-cone-size.txt'
    )
    parser.add_argument(
        '--SCION_core_topo',
        default='data/scion/20230101.SCION_core_topo.txt'
    )

    # Other info
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

def report_country_net_info(args):

    def _get_info_bgp(country):
        mainland = get_mainland(as_topo, as_info, country)
        border_ases = get_border_ases(as_topo, mainland)

        mainland_size = len(mainland)
        border_size_bgp = len(border_ases)
        border_perc_bgp = round(100 * border_size_bgp / mainland_size)
        return mainland_size, border_size_bgp, border_perc_bgp

    def _has_foreign_connection(core_asn, isd_core_topo):
        isd_cores_set = set(isd_core_topo.keys())
        for conn in scion_core_topo[core_asn]['cores']:
            if conn not in isd_cores_set:
                return True
        return False
    
    def _get_info_scion(country, mainland_size):
        isd_core_topo, _ = get_isd_topos(
            scion_core_topo, as_topo, cones, as_info, country
        )

        border_ases = [
            core_asn for core_asn in isd_core_topo.keys()
            if _has_foreign_connection(core_asn, isd_core_topo)
        ]
        border_size_scion = len(border_ases)
        border_perc_scion = round(100 * border_size_scion / mainland_size)
        return border_size_scion, border_perc_scion

    data = list()
    header = ['', 'Mainland size', 'Border ASes (BGP)', 'Border ASes (SCION)']
    for country in COUNTRIES:
        mainland_size, border_size_bgp, border_perc_bgp = _get_info_bgp(country)
        border_size_scion, border_perc_scion = _get_info_scion(
            country, mainland_size
        )

        # Reporting results
        if LATEX_PRINT:
            latex_p = (
                f'{country_name(country)} & {mainland_size} & '
                f'{border_size_bgp} ({border_perc_bgp}\%)  & '
                f'{border_size_scion} ({border_perc_scion}\%) \\\\ '
            )
            print(latex_p)
        else:
            data.append([
                country_name(country),
                f'{mainland_size}',
                f'{border_size_bgp} (\033[1;32m{border_perc_bgp}\033[00m %)',
                f'{border_size_scion} (\033[1;32m{border_perc_scion}\033[00m %)'
            ])
    
    if not LATEX_PRINT: print(tabulate(data, headers=header))

if __name__ == '__main__':
    args = _parse_args()
    _set_global_vars(args)

    report_country_net_info(args)
