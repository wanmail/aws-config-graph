import json

from neo4j import Driver

from mypy_boto3_config.type_defs import ConfigurationItemTypeDef

from index import PRIMARY_KEY, get_resource_label


def merge_relationship(driver: Driver, src_id, src_type, dst_id, dst_type, relationship):
    src_label = get_resource_label(src_type)
    dst_label = get_resource_label(dst_type)

    relationship = relationship.replace(" ", "_")

    query = f"""MATCH (a:{src_label} {{{PRIMARY_KEY}: '{src_id}'}}), (b:{dst_label} {{{PRIMARY_KEY}: '{dst_id}'}})
        MERGE (a)-[:{relationship}]->(b)"""

    with driver.session() as session:
        session.run(query)


def merge_node(driver: Driver, id: str, typ: str, obj: dict):
    label = get_resource_label(typ)

    query = f"MERGE (n:{label} {{{PRIMARY_KEY}: '{id}'}}) \n"

    if obj != None and obj != {}:

        for k, v in obj.items():
            if type(v) == list or type(v) == dict:
                obj[k] = json.dumps(v)

        fields = ",\n".join(
            [f"    n.{key} = ${key}" for key in obj.keys()]) + "\n"

        query += "ON CREATE SET \n"
        query += fields

        query += "ON MATCH SET \n"
        query += fields

    query += "RETURN n"

    with driver.session() as session:
        session.run(query, obj)
            


def merge_item(driver: Driver, item: ConfigurationItemTypeDef):
    id = item.pop('resourceId')
    typ = item.pop('resourceType')

    rels = item.pop('relationships', [])

    for key in list(item.keys()):
        if key.startswith('configurationItem'):
            item.pop(key)

    merge_node(driver, id, typ, item)

    for rel in rels:
        rel_id = rel.pop('resourceId')
        rel_typ = rel.pop('resourceType')
        # relationshipName is called name in S3 snapshot
        rel_name = rel.pop('relationshipName', rel.pop('name', "unknown_relationship"))

        merge_node(driver, rel_id, rel_typ, rel)
        merge_relationship(driver, id, typ, rel_id, rel_typ, rel_name)
