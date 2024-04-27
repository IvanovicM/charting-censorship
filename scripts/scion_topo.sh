################################################################################
# conda create -n cens python=3.10.4

conda activate cens
echo -e "\xE2\x9C\x94 SCION core topo"

# 1. Generate customer cone size
echo -e "  \xe2\x86\xb3 [1/2] Calculating customer cone size"
python -m source.simulation.scion.conesize

# 2. Core topo
echo -e "  \xe2\x86\xb3 [2/2] Generating core SCION topo."
python -m source.simulation.scion.sciongen

# Done!
echo -e "  \xe2\x86\xb3 Finished!\n"
