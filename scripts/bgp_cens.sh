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

# 1. Calculate choke potential of each border AS of the country mainland
echo -e "  \xe2\x86\xb3 [1/2] Choke Potential of border ASes of the mainland (choke_potential.py)."
python -m source.simulation.bgp.choke_potential --country ${COUNTRY} --dataset ${DATASET}

# 2. Calculate BGP results.
echo -e "  \xe2\x86\xb3 [2/2] BGP results with various N (bgp_censorship_metric.py)."
python -m source.simulation.bgp.bgp_censorship_metric --country ${COUNTRY} --dataset ${DATASET}

# Done!
echo -e "  \xe2\x86\xb3 Finished!\n"
