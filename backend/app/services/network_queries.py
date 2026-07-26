from app.graph_db import run_cypher


def _node(id_, label, props):
    """Cytoscape.js-friendly node shape: {data: {id, label, type, ...}}"""
    node_id = f"{label}:{id_}"
    return {"data": {"id": node_id, "type": label, **props}}


def _edge(source_label, source_id, target_label, target_id, rel_type):
    source = f"{source_label}:{source_id}"
    target = f"{target_label}:{target_id}"
    return {"data": {"id": f"{source}->{rel_type}->{target}", "source": source, "target": target, "label": rel_type}}


def get_accused_network(accused_id: int, depth: int = 2):
    """Everything connected to one accused person, out to `depth` hops —
    crimes they're tied to, vehicles involved in those crimes, and other
    accused who share those same crimes or vehicles."""
    query = f"""
    MATCH (a:Accused {{id: $accused_id}})
    OPTIONAL MATCH path = (a)-[*1..{depth}]-(connected)
    WITH a, collect(path) AS paths
    RETURN a, paths
    """
    records = run_cypher(query, {"accused_id": accused_id})
    if not records or records[0]["a"] is None:
        return {"nodes": [], "edges": []}

    nodes = {}
    edges = {}

    def add_node(n):
        labels = list(n.labels) if hasattr(n, "labels") else []
        label = labels[0] if labels else "Unknown"
        props = dict(n)
        node_id = f"{label}:{props.get('id')}"
        nodes[node_id] = _node(props.get("id"), label, props)

    def add_rel(rel, start_node, end_node):
        start_label = list(start_node.labels)[0]
        end_label = list(end_node.labels)[0]
        e = _edge(start_label, dict(start_node).get("id"), end_label, dict(end_node).get("id"), rel.type)
        edges[e["data"]["id"]] = e

    for record in records:
        for path in record["paths"]:
            if path is None:
                continue
            for n in path.nodes:
                add_node(n)
            for rel in path.relationships:
                add_rel(rel, rel.start_node, rel.end_node)

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def get_crime_network(crime_id: int):
    """Everything directly connected to one crime: accused, victim, vehicle."""
    query = """
    MATCH (c:Crime {id: $crime_id})
    OPTIONAL MATCH (c)<-[r1:ACCUSED_IN]-(a:Accused)
    OPTIONAL MATCH (c)-[r2:HAS_VICTIM]->(vi:Victim)
    OPTIONAL MATCH (c)-[r3:INVOLVES_VEHICLE]->(v:Vehicle)
    RETURN c, collect(DISTINCT a) AS accused, collect(DISTINCT vi) AS victims, collect(DISTINCT v) AS vehicles
    """
    records = run_cypher(query, {"crime_id": crime_id})
    if not records or records[0]["c"] is None:
        return {"nodes": [], "edges": []}

    record = records[0]
    nodes = {}
    edges = {}

    c = record["c"]
    c_props = dict(c)
    nodes[f"Crime:{c_props['id']}"] = _node(c_props["id"], "Crime", c_props)

    for a in record["accused"]:
        if a is None:
            continue
        a_props = dict(a)
        nodes[f"Accused:{a_props['id']}"] = _node(a_props["id"], "Accused", a_props)
        e = _edge("Accused", a_props["id"], "Crime", c_props["id"], "ACCUSED_IN")
        edges[e["data"]["id"]] = e

    for vi in record["victims"]:
        if vi is None:
            continue
        vi_props = dict(vi)
        nodes[f"Victim:{vi_props['id']}"] = _node(vi_props["id"], "Victim", vi_props)
        e = _edge("Crime", c_props["id"], "Victim", vi_props["id"], "HAS_VICTIM")
        edges[e["data"]["id"]] = e

    for v in record["vehicles"]:
        if v is None:
            continue
        v_props = dict(v)
        nodes[f"Vehicle:{v_props['id']}"] = _node(v_props["id"], "Vehicle", v_props)
        e = _edge("Crime", c_props["id"], "Vehicle", v_props["id"], "INVOLVES_VEHICLE")
        edges[e["data"]["id"]] = e

    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def get_hidden_connections(limit: int = 25):
    """THE headline query: find vehicles used in crimes by different accused,
    in different districts — a connection a human cross-checking FIRs by hand
    would very likely miss. This is what makes Module 2 the 'wow' moment."""
    query = """
    MATCH (a1:Accused)-[:ACCUSED_IN]->(c1:Crime)-[:INVOLVES_VEHICLE]->(v:Vehicle)
          <-[:INVOLVES_VEHICLE]-(c2:Crime)<-[:ACCUSED_IN]-(a2:Accused)
    WHERE a1.id < a2.id AND c1.district <> c2.district
    RETURN DISTINCT v.id AS vehicle_id, v.plate_no AS plate_no, v.vehicle_type AS vehicle_type,
           a1.id AS accused_1_id, a1.name AS accused_1_name,
           c1.id AS crime_1_id, c1.fir_no AS crime_1_fir, c1.district AS crime_1_district,
           a2.id AS accused_2_id, a2.name AS accused_2_name,
           c2.id AS crime_2_id, c2.fir_no AS crime_2_fir, c2.district AS crime_2_district
    LIMIT $limit
    """
    return [dict(record) for record in run_cypher(query, {"limit": limit})]


def get_repeat_offenders(limit: int = 25):
    """Accused linked to the most crimes, with crime-type breakdown — surfaces
    the planted repeat-offender pattern from Phase 0's data generator."""
    query = """
    MATCH (a:Accused)-[:ACCUSED_IN]->(c:Crime)
    WITH a, count(c) AS crime_count, collect(DISTINCT c.crime_type) AS crime_types,
         collect(DISTINCT c.district) AS districts
    WHERE crime_count > 1
    RETURN a.id AS accused_id, a.name AS name, a.is_repeat_offender AS flagged_repeat_offender,
           crime_count, crime_types, districts
    ORDER BY crime_count DESC
    LIMIT $limit
    """
    return [dict(record) for record in run_cypher(query, {"limit": limit})]
