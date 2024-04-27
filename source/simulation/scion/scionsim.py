from collections import defaultdict, deque
from functools import cmp_to_key

# ==============================================================================
# ===============================  UTILS  ======================================
# ==============================================================================

def cores_within_reach(isd_core_topo, core_destination, censors=set()):

    def _traverse(node, visited):        
        if node in censors:
            return visited

        visited[node] = True
        for conn in isd_core_topo[node]['cores']:
            if not visited[conn]:
                visited = _traverse(conn, visited)
        return visited
    
    def _get_within_reach(visited):
        reachable = set([x for x, v in visited.items() if v])
        return reachable

    if core_destination not in isd_core_topo.keys(): return set()
    
    visited = defaultdict(bool)
    visited = _traverse(core_destination, visited)
    return _get_within_reach(visited)

def non_cores_within_reach(
    cores, isd_non_core_topo, core_destination, censors=set()
):

    def _get_next_visit_rels(visiting_rel):
        # What am I (visiting_rel) to this node that forwarded to me?
        # Based on that I am forwarding to others.
        if visiting_rel == 'providers':
            return ['customers', 'providers', 'peers']
        return ['customers']

    def _traverse(node, visited_from, visiting_rel):
        if node == core_destination:
            return visited_from
        
        if node in censors:
            return visited_from

        visited_from[node][visiting_rel] = True
        next_visit_rels = _get_next_visit_rels(visiting_rel)
        for rel in next_visit_rels:
            for conn in isd_non_core_topo[node][rel]:
                if not visited_from[conn][rel]:
                    visited_from = _traverse(conn, visited_from, rel)
        return visited_from
    
    def _get_within_reach(visited_from):
        reachable = set([
            x for x, visited in visited_from.items()
            if x not in cores and
            (visited['peers'] or visited['customers'] or visited['providers'])
        ])
        return reachable

    if core_destination not in isd_non_core_topo.keys(): return set()
    
    visited_from = defaultdict(lambda: defaultdict(bool))
    for rel in ['customers', 'providers', 'peers']:
        for conn in isd_non_core_topo[core_destination][rel]:
            visited_from = _traverse(conn, visited_from, rel)
    return _get_within_reach(visited_from)

# ==============================================================================
# ================================  ISD  =======================================
# ==============================================================================

def cores_within_foreign_reach(
    scion_core_topo, isd_core_topo, as_info, country, censors=set()
):

    def _has_foreign_connection(asn):
        isd_cores_set = set(isd_core_topo.keys())
        for conn in scion_core_topo[asn]['cores']:
            if conn not in isd_cores_set:
                return True
        return False
    
    def _get_cores_with_foreign_connection(cores):
        return set([
            asn for asn in cores if _has_foreign_connection(asn)
        ])

    def _get_foreign_reachable_from_cores():
        core2reachable = defaultdict(set)
        for core in cores:
            core_reach = cores_within_reach(isd_core_topo, core, censors)
            core2reachable[core] = core_reach
        return core2reachable
    
    def _get_core_reach(cores, cores_with_foreign, core2reachable):
        cores_reach = set()
        for core in cores:
            if core in censors: continue

            for core_foreign in cores_with_foreign:
                if core == core_foreign or core in core2reachable[core_foreign]:
                    cores_reach.update([core])
                    break
        return cores_reach

    cores = set(isd_core_topo.keys())
    cores_with_foreign = _get_cores_with_foreign_connection(cores)
    core2reachable = _get_foreign_reachable_from_cores()
    core_reach = _get_core_reach(cores, cores_with_foreign, core2reachable)
        
    return core_reach

def non_cores_within_foreign_reach(
    scion_core_topo, isd_core_topo, isd_non_core_topo, as_info, country,
    censors=set()
):

    def _has_foreign_connection(asn):
        isd_cores_set = set(isd_core_topo.keys())
        for conn in scion_core_topo[asn]['cores']:
            if conn not in isd_cores_set:
                return True
        return False
    
    def _get_cores_with_foreign_connection(cores):
        return set([
            asn for asn in cores if _has_foreign_connection(asn)
        ])

    def _get_foreign_reachable_from_cores():
        core2reachable = defaultdict(set)
        for core in cores:
            core_reach = cores_within_reach(isd_core_topo, core, censors)
            core2reachable[core] = core_reach
        return core2reachable
    
    def _get_non_core_reach(cores, cores_with_foreign, core2reachable):
        non_cores_reach = set()
        for core in cores:
            if core in censors: continue

            new_nodes = non_cores_within_reach(
                cores, isd_non_core_topo, core, censors
            )

            for core_foreign in cores_with_foreign:
                if core == core_foreign or core in core2reachable[core_foreign]:
                    non_cores_reach.update(new_nodes)
                    break
        return non_cores_reach

    cores = set(isd_core_topo.keys())
    cores_with_foreign = _get_cores_with_foreign_connection(cores)
    core2reachable = _get_foreign_reachable_from_cores()

    non_cores_reach = _get_non_core_reach(
        cores, cores_with_foreign, core2reachable
    ) 
    return non_cores_reach

def nodes_within_foreign_reach(
    scion_core_topo, isd_core_topo, isd_non_core_topo, as_info, country,
    censors=set()
):
    reach_non_core = non_cores_within_foreign_reach(
        scion_core_topo, isd_core_topo, isd_non_core_topo, as_info, country,
        censors
    )
    reach_core = cores_within_foreign_reach(
        scion_core_topo, isd_core_topo, as_info, country, censors
    )
    return reach_non_core.union(reach_core)

# ==============================================================================
# ===============================  CORE  =======================================
# ==============================================================================

def graph_components_wo_hegs(scion_core_topo, as_info, heg_countries):

    def _country_origin(asn):
        return as_info[asn]

    def _get_component(start_asn, visited):
        q = deque()
        q.append(start_asn)
        visited[start_asn] = True

        component = list()
        component.append(start_asn)

        while q:
            curr_asn = q.popleft()
            for conn in scion_core_topo[curr_asn]['cores']:
                if _country_origin(conn) in heg_countries: continue
                if not visited[conn]:
                    visited[conn] = True
                    q.append(conn)
                    component.append(conn)
        return component, visited

    def _get_components():
        visited = defaultdict(bool)

        components = list()
        for start_asn in scion_core_topo.keys():
            if _country_origin(start_asn) in heg_countries: continue
            if not visited[start_asn]:
                component, visited = _get_component(start_asn, visited)
                components.append(component)
        return components
    
    def _sort_components(components):
        
        def _islands_cmp(a, b):
            if len(a) > len(b): return -1
            return 1

        components.sort(key=cmp_to_key(_islands_cmp))
        return components

    components = _get_components()
    return _sort_components(components)