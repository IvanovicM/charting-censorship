from collections import defaultdict, deque
from functools import cmp_to_key

def in_country(asn, country, as_country_map):
    if isinstance(as_country_map[asn], list):
        # Multiple country origin
        return country in as_country_map[asn]
    return as_country_map[asn] == country

def get_mainland(as_topo, as_country_map, country):
    '''
        Returns the mainland, given country labeling of the ASes.
        Each AS must have at most one country label.

        Args:
            as_topo: AS topology
            as_country_map: AS info on country origin (CAIDA or CYMRU with one
                country, or RIPE with multiple country origin)
            country: 2-letter country code
        
        Returns:
            Set of ASes that are in mainland
            ==> S = mainland; D = non-mainland
    '''

    def _get_country_asns():
        return [
            asn for asn in as_topo.keys()
            if in_country(asn, country, as_country_map)
        ]

    def _get_island(start_asn):
        q = deque()
        q.append(start_asn)

        visited = defaultdict(bool)
        visited[start_asn] = True

        island = list()
        island.append(start_asn)

        while q:
            curr_asn = q.popleft()
            rels = as_topo[curr_asn]
            all_conns = rels['providers'] + rels['customers'] + rels['peers']
            for conn in all_conns:
                if not in_country(conn, country, as_country_map):
                    continue
                if not visited[conn]:
                    visited[conn] = True
                    q.append(conn)
                    island.append(conn)
        return island

    def _get_island_size(start_asn, visited):
        island = _get_island(start_asn)
        island_size = len(island)
        for asn in island: visited[asn] = True
        return island_size, visited

    def _get_islands(country_asns):
        country_islands = list()
        visited = defaultdict(bool)
        for asn in country_asns:
            if not visited[asn]:
                island_size, visited = _get_island_size(asn, visited)
                country_islands.append((asn, island_size))
        return country_islands

    def _get_country_islands():
        
        def _islands_cmp(a, b):
            if a[1] > b[1]: return -1
            return 1

        country_asns = _get_country_asns()
        country_islands = _get_islands(country_asns)
        country_islands.sort(key=cmp_to_key(_islands_cmp))
        return country_islands

    country_islands = _get_country_islands()
    mainland_start_asn, _ = country_islands[0]
    return set(_get_island(mainland_start_asn))

def get_border_ases(as_topo, mainland):
    border_ases = list()
    for asn in mainland:
        # The AS _in_ the country...
        rels = as_topo[asn]

        # ...with a connection _outside_ the country
        all_connections = rels['customers'] + rels['peers'] + rels['providers']
        for connection in all_connections:
            if connection not in mainland:
                border_ases.append(asn)
                break

    return border_ases
