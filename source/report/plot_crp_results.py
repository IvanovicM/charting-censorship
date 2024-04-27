import argparse
import json
import matplotlib.pyplot as plt
import sys

from source.utils.utils import check_make_save_file_dir, country_name

COUNTRIES_TO_PLOT = ['AU', 'FR', 'DE', 'IT', 'NL', 'SG', 'ZA', 'UA']
COUNTRY_COLORS = {
    'AU': '#ff7f00',
    'FR': '#e41a1c',
    'DE': '#4daf4a',
    'IT': '#f1c232',
    'NL': '#377eb8',
    'SG': '#984ea3',
    'ZA': '#a65628',
    'UA': '#f781bf',
}

X_LABEL = '$\mathit{Number\ of\ censoring\ ASes\ (N)}$'
Y_LABEL = '$\mathit{Censorship\ Resilience\ Potential}$'

MAX_N = 20

# font size
fs = 14

def _parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--dataset', default='CAIDA_HYBRID', required=True,
        choices=['CAIDA_HYBRID']
    )
    parser.add_argument(
        '--arch', default='BGP', required=True,
        choices=['BGP', 'VPN', 'SCION', 'all']
    )
    parser.add_argument(
        '--results_file',
        default='results/CRP.ALL.results/20230101.as-rel2'
    )
    parser.add_argument(
        '--fig_save_file',
        default='results/CRP.ALL.results.graphs/20230101.as-rel2'
    )

    return parser.parse_args()

def _check_metadata(data, cone_size_scion=True, perc=False):
    if (
        data['metadata']['perc'] == perc and
        data['metadata']['cone_size_scion'] == cone_size_scion
    ):
        return True
    return False

def _save_fig_pdf(save_file, dataset, arch):
    check_make_save_file_dir(save_file)
    plt.savefig(f'{save_file}.{dataset}.{arch}.pdf', bbox_inches='tight')

def plot_results_on_ax(data, ax, arch='BGP'):
    for country in COUNTRIES_TO_PLOT:
        x = list(int(n) for n in data[country][arch].keys() if int(n)<=MAX_N)
        y = list(data[country][arch][str(n)] for n in x)

        color = COUNTRY_COLORS[country]
        label = country_name(country)
        ax.plot(x, y, color, label=label)
    
    ax.set_title('Waypoint' if arch == 'VPN' else arch, fontsize=fs, alpha=0.7)
    ax.set_xlim([0, MAX_N])
    ax.set_ylim([0, 1])
    ax.set_xticks([x for x in range(0, MAX_N+1, MAX_N//4)])
    ax.set_box_aspect(0.95)
    ax.grid(axis='y', alpha=0.3)

def plot_results_separate(data, arch='BGP'):
    ax = plt.subplot(111)
    plot_results_on_ax(data, ax, arch=arch)

    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(Y_LABEL)

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    _save_fig_pdf(args.fig_save_file, args.dataset, arch)

def plot_results_combined(data, args):
    fig, (ax_bgp, ax_vpn, ax_scion) = plt.subplots(1, 3, sharey=True, figsize=(14, 7))

    plot_results_on_ax(data, ax_bgp, arch='BGP')
    plot_results_on_ax(data, ax_vpn, arch='VPN')
    plot_results_on_ax(data, ax_scion, arch='SCION')

    ax_bgp.set_ylabel(Y_LABEL, fontsize=fs, alpha=0.7)
    ax_vpn.set_xlabel(X_LABEL, fontsize=fs, alpha=0.7)

    plt.legend(bbox_to_anchor=(0.905, 0.755), loc="lower right", bbox_transform=fig.transFigure, ncol=8, fontsize=12)
    plt.tight_layout()
    _save_fig_pdf(args.fig_save_file, args.dataset, args.arch)
    #plt.show()

if __name__ == '__main__':
    args = _parse_args()

    file_name = f'{args.results_file}.{args.dataset}.json'
    with open(file_name, 'r') as f:
        data = json.load(f)
        if not _check_metadata(data):
            print('Provided metadata not matching')
            sys.exit()

        if args.arch == 'all':
            plot_results_combined(data, args)
        else:
            plot_results_separate(data, arch=args.arch)
