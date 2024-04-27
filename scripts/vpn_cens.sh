################################################################################
# conda create -n cens python=3.10.4

conda activate cens
echo -e "All logs available in the dir: logs.\n"

################################################################################

# 0. Generate all routes
# echo -e "\xE2\x9C\x94 [0/2] Generating all BGP routes (quicksand.py)."
# python -m source.simulation.bgp.quicksand

################################################################################
# Country-based simulations for multiple datasets
################################################################################

COUNTRY="CH"
DATASET="CAIDA_HYBRID"
echo -e "\xE2\x9C\x94 Country: $COUNTRY; Dataset: $DATASET"

# 1. Calculate VPN (waypoint) results.
echo -e "  \xe2\x86\xb3 [1/1] VPN results with various N (vpn_censorship_metric.py)."
python -m source.simulation.vpn.vpn_censorship_metric -c ${COUNTRY} --dataset ${DATASET} --vpnmethod MaxMind-AnonG

# Done!
echo -e "  \xe2\x86\xb3 Finished!\n"
