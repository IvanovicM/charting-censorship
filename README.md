# README

The code repository accompanying our article: [**Charting Censorship Resilience and Global Internet Reachability: A Quantitative Approach**](https://arxiv.org/abs/2403.09447).

**Citation**

```
@inproceedings{ivanovic2024charting,
  title = {Charting Censorship Resilience and Global Internet Reachability: A Quantitative Approach},
  author = {Ivanović, Marina and Wirz, François and Subirà Nieto, Jordi and Perrig, Adrian},
  booktitle={IFIP Networking Conference},
  publisher={IFIP},
  year = {2024}
}
```

## Setup

```shell
conda create -n cens python=3.10.4
conda activate cens
pip install -r requirements.txt
```

## Data analysis

**Country Network Stats**

```shell
python -m source.report.report_country_net_stats --dataset CAIDA_HYBRID
```

**Visualize country network**

```shell
COUNTRY='CH' # Choose 2-letter country code
python -m source.data.country_topo_stats --vis --dataset CAIDA_HYBRID --country $COUNTRY
```

## Simulation

**Censorship Resilience Potential**

```shell
source ./scripts/bgp_cens.sh
source ./scripts/vpn_cens.sh
```

**Global reachability**

```shell
source ./scripts/global_reach.sh
```

**SCION topo**

```shell
source ./scripts/scion_topo.sh
```

## Obtaining results

**Censorship Resilience Potential** 

```shell
# Report results in a table
python -m source.report_crp_results --vpnmethod MaxMind-AnonG --dataset CAIDA_HYBRID --report
python -m source.report_crp_results --vpnmethod MaxMind-AnonG --dataset CAIDA_HYBRID --no-report --save

# Reports results as a graph
ARCH='BGP' # arch options: BGP, VPN, SCION, all
python -m source.report.plot_crp_results --dataset CAIDA_HYBRID --arch ${ARCH}
```

**Global Reachability Potential**

```shell
# Report results in a table
python -m source.report_grp_results --dataset CAIDA_HYBRID
```

**Results**

Results presented in the paper, extended and more comprehensive, are presented in the directory ```results```.
