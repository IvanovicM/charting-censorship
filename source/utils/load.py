import json

from collections import defaultdict

def load_clean_CAIDA_data(topo_file, as_org_file):

    def clean_info_dataset(as_topo, as_info):
        as_info_clean  = defaultdict(lambda: defaultdict(str))
        for asn, as_i in as_info.items():
            if asn in as_topo.keys():
                as_info_clean[asn] = as_i
        return as_info_clean

    as_topo = load_AS_topology(topo_file)
    org_info, as_info = load_ORG_AS_info(as_org_file)
    as_info = clean_info_dataset(as_topo, as_info)
    return as_topo, as_info, org_info

def load_AS_topology(topology_file):
    '''
        File contains provider2customer & peer2peer relationships. Format:
            <provider-as>|<customer-as>|-1|<source> OR
            <peer-as>|<peer-as>|0|<source>
        The return dict:
            topology[ASN] = {'customers':[], 'peers':[], 'providers':[]}
    '''
    topology = defaultdict(lambda: defaultdict(list))

    with open(topology_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                arr = line.strip().split('|')
                asn1, asn2, rel_type = arr[0], arr[1], int(arr[2])

                if rel_type == -1:
                    topology[asn1]['customers'].append(asn2)
                    topology[asn2]['providers'].append(asn1)
                else:
                    topology[asn1]['peers'].append(asn2)
                    topology[asn2]['peers'].append(asn1)
    return topology

def load_ORG_AS_info(as_org_info_file):
    '''
        Part 1 contains info about orgs. Format:
            org_id|changed|name|country|source
        The return dict:
            org_info[org_id] = {'org_name':<str>, 'country':<str>}

        Part 2 contains info about ASes. Format:
            aut|changed|aut_name|org_id|opaque_id|source
        The return dict:
            as_info[ASN] = {'as_name':<str>, 'org_id':<str>}
    '''
    org_info = defaultdict(lambda: defaultdict(str))
    as_info  = defaultdict(lambda: defaultdict(str))

    orgs_parsed = False
    orgs_parsing = False

    with open(as_org_info_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                if not orgs_parsed: orgs_parsing = True

                # Parse either first part (orgs) or second part (ASes)
                arr = line.strip().split('|')
                if not orgs_parsed:
                    org_id, _, org_name, c = arr[0], arr[1], arr[2], arr[3]
                    org_info[org_id]['org_name'] = org_name
                    org_info[org_id]['country'] = c
                else:
                    asn, _, asn_name, org_id = arr[0], arr[1], arr[2], arr[3]
                    as_info[asn]['as_name'] = asn_name
                    as_info[asn]['org_id'] = org_id
            else:
                if orgs_parsing: orgs_parsed = True
    return org_info, as_info 

def load_routing_topo(topo_file):
    '''
        The file should contain the routing info (e.g. obtained by the BGP
        simulation).

        Format:
            # Destination
            <dest>
            # Routing topo
            #
            # Format:
            # ASN|next_hop
            <routing_info>
            ...
    '''
    routing_topo = defaultdict(str)

    destination_parsed = False
    destination_parsing = False
    with open(topo_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                if not destination_parsed: destination_parsing = True

                # Parse either first part (dest) or second part (routing info)
                if not destination_parsed:
                    destination = line.strip()
                else:
                    arr = line.strip().split('|')
                    asn, next_hop = arr[0], arr[1]
                    routing_topo[asn] = next_hop
            else:
                if destination_parsing: destination_parsed = True
    return destination, routing_topo

def load_RIPE_geo_address(geo_address_file):
    '''
        File contains geo data about ASes, fetched using RIPE API
            example: {
                "asn": "9730",
                "IN": {"ipv4": 2048, "ipv6": 3626777458843887524118528},
                "ZA": {"ipv4": 256, "ipv6": 0}
            }
        The return dict (the list of country origins, with their address space):
            geo data about relevant ASes
            example: "9730": {
                "IN": {"ipv4": 2048, "ipv6": 3626777458843887524118528},
                "ZA": {"ipv4": 256, "ipv6": 0}
            }
    '''
    as_info = defaultdict()

    with open(geo_address_file) as f:
        for line in f:
            if line.strip() == '': continue
            dict_info = json.loads(line.strip())
            asn = dict_info['asn']
            del dict_info['asn']
            as_info[asn] = dict_info

    return as_info

def load_RIPE_geo_countries(geo_address_file):
    '''
        File contains geo data about ASes, fetched using RIPE API
            example: {
                "asn": "9730",
                "IN": {"ipv4": 2048, "ipv6": 3626777458843887524118528},
                "ZA": {"ipv4": 256, "ipv6": 0}
            }
        The return dict (the list of country origins):
            geo data about relevant ASes
            example: "9730": ["IN", "ZA"]
    '''
    geo_load = load_RIPE_geo_address(geo_address_file)
    return {
        asn: [
            country for country in countries.keys()
            if country != '?'
        ]
        for asn, countries in geo_load.items()
    }

def load_choke_potentials(chokepoint_file):
    '''
        The file should contain chokepoint info about border ASes of a certain
        country.

        Format:
            # Country info
            #
            # Format:
            # Country|total_path_cnt_outflow
            ...
            # Chokepoint potentials
            #
            # Format:
            # Border_ASN|intercepted_outflow_cnt
            ...
    '''
    cpp = defaultdict(int)

    country_parsed = False
    country_parsing = False
    with open(chokepoint_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                if not country_parsed: country_parsing = True
                arr = line.strip().split('|')

                # Parse either first part (country) or second part (cpp info)
                if not country_parsed:
                    country = arr[0]
                    total_cnt_outflow = int(arr[1])
                else:
                    border_as = arr[0]
                    cpp[border_as] = int(arr[1])
            else:
                if country_parsing: country_parsed = True
    return country, total_cnt_outflow, cpp

def load_SCION_core_topo_no_rels(scion_core_topo_file):
    '''
        The file contains info about links between core ASes.
        Format:
            core_ASN|core_ASN|<optional: link type>        
        Return: a dict
            scion_core_topo[ASN]= {'cores':[]}
    '''
    scion_core_topo = defaultdict(lambda: defaultdict(list))

    with open(scion_core_topo_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                arr = line.strip().split('|')
                asn1, asn2 = arr[0], arr[1]

                scion_core_topo[asn1]['cores'].append(asn2)
                scion_core_topo[asn2]['cores'].append(asn1)

    return scion_core_topo

def load_customer_cone(file_name):
    '''
        The file customer cone info. ASes are sorted by their customer cone.
        Format: idx|ASN|customer_cone
        The return dict:
            dict[ASN] = <customer_cone>
    '''
    customer_cone = defaultdict(int)

    for line in open(file_name):
        if not line.strip().startswith("#"):
            arr = line.strip().split('|')
            _, asn, cc = arr[0], arr[1], int(arr[2])
            customer_cone[asn] = cc
    return customer_cone

def load_from_json(json_file):
    as_per_country = defaultdict()
    with open(json_file, 'r') as f:
        as_per_country = json.load(f)
    return as_per_country

def load_bgp_crp_results(bgp_results_file):
    '''
        The file should contain CRP results info about border ASes of a certain
        country.

        Format:
            # Country info
            #
            # Format:
            <Country>

            # Info about censors
            # Format:
            <total_potential_censor_num>
            censors_num_N|censor_1,censor_2,...,censor_N
            
            # Chokepoint potentials
            #
            # Format:
            censor_num|total_reach_outflow_path
    '''
    censors_by_num = defaultdict(set)
    results_by_num = defaultdict(int)

    part_parsing = 1
    comment_parsing = True
    with open(bgp_results_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                comment_parsing = False

                if part_parsing == 1:
                    country = line.strip()
                elif part_parsing == 2:
                    arr = line.strip().split('|')
                    if len(arr) == 1: total_potential_censors = int(arr[0])
                    else:
                        censors = arr[1].strip().split(',')
                        censors_by_num[int(arr[0])] = set(censors)
                else:
                    arr = line.strip().split('|')
                    results_by_num[int(arr[0])] = int(arr[1])
            else:
                if not comment_parsing:
                    part_parsing += 1
                    comment_parsing = True
    return country, censors_by_num, total_potential_censors, results_by_num

def load_hegemony_info(hegemony_file):
    '''
        The file should contain hegemony info about the given country.

        Format:
            # Country info
            #
            # Format:
            # Country|total_path_cnt|not_intercepted_cnt
            ...
            # Chokepoint potentials
            #
            # Format:
            # Country|intercepted_path_cnt
            ...
    '''
    heg = defaultdict(int)

    country_parsed = False
    country_parsing = False
    with open(hegemony_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                if not country_parsed: country_parsing = True
                arr = line.strip().split('|')

                # Parse either first part (country) or second part (hegemony info)
                if not country_parsed:
                    country = arr[0]
                    total_path_cnt = int(arr[1])
                    interception_free = int(arr[2]) if arr[2] != "None" else None
                else:
                    foreign_country = arr[0]
                    heg[foreign_country] = int(arr[1])
            else:
                if country_parsing: country_parsed = True
    return country, total_path_cnt, interception_free, heg

def load_as_info(filename):
    '''
        File contains info about ASes obtained from Team Cymru or CAIDA (with
        minor post-processing).
        
        The return dict:
            as_info[ASN] = alpha2_country_code_1, ..., alpha2_country_code_N
    '''
    as_info = defaultdict(list)

    with open(filename) as f:
        for line in f:
            if not line.strip().startswith("#"):
                arr = line.strip().split('|')
                asn, countries = arr[0].strip(), arr[1].strip().split(',')
                as_info[asn] = countries
    return as_info

def load_AS_list(as_list_file):
    '''
        File should contain only the list of ASes, each ASN in a new line
        Returns: list of ASes from the file
    '''
    as_list = list()
    with open(as_list_file) as f:
        for line in f:
            if not line.strip().startswith("#"):
                asn = line.strip()
                as_list.append(asn)
    return as_list

def load_global_reach_info(file_name):
    '''
        Returns: heg_group, heg_countries, total_path_cnt, int_free_path_cnt
    # '''
    line_num = 1
    with open(file_name) as f:
        for line in f:
            if not line.strip().startswith("#"):
                arr = line.strip().split('|')

                if line_num == 1:
                    heg_group = arr[0]
                    heg_countries = list(arr[1].strip().split(','))
                elif line_num == 2:
                    total_path_cnt = int(arr[1].strip())
                    int_free_path_cnt = int(arr[2].strip())
                line_num += 1
                
    return heg_group, heg_countries, total_path_cnt, int_free_path_cnt
