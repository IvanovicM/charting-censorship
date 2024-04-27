################################################################################
# conda create -n cens python=3.10.4

conda activate cens
echo -e "All logs available in the dir: logs.\n"

# 0. Generate all routes
# echo -e "\xE2\x9C\x94 [0/2] Generating all BGP routes (quicksand.py)."
# python -m source.simulation.bgp.quicksand

################################################################################
# Global reach, with fixed hegemons/countries to circumvent
################################################################################

COUNTRY="CH"
DATASET="CAIDA_HYBRID"
HEGS="United-States'
echo -e "\xE2\x9C\x94 Country: $COUNTRY; Dataset: $DATASET"

# 1. Global reachability for BGP
echo -e "  \xe2\x86\xb3 [1/2] Global reachability for BGP"
conda activate msc && python -m source.simulation.bgp.bgp_global_reach --dataset ${DATASET} --hegemons ${HEGS}

# 2. Global reachability for VPN
echo -e "  \xe2\x86\xb3 [2/2] Global reachability for VPN"
conda activate msc && python -m source.simulation.vpn.vpn_global_reach --dataset ${DATASET} --hegemons ${HEGS}

# Done!
echo -e "  \xe2\x86\xb3 Finished!\n"
