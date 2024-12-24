import http.client
import json
import ssl

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ClientError

RULE_ALREADY_EXISTS = "Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists"
INDEX_ALREADY_EXISTS = "Neo.ClientError.Schema.IndexAlreadyExists"
CONSTRAINT_ALREADY_EXISTS = "Neo.ClientError.Schema.ConstraintAlreadyExists"


def get_repo_files(owner, repo, path='', token=None) -> list[dict]:
    """
    Fetches the list of files in a given GitHub repository path.

    Refer to https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#get-repository-content.

    Args:
        owner (str): The owner of the repository.
        repo (str): The name of the repository.
        path (str, optional): The path within the repository to list files from. Defaults to ''.
        token (str, optional): The GitHub token for authentication. Defaults to None.
    Returns:
        list: A list of files in the specified repository path.
    Raises:
        http.client.HTTPException: If an error occurs during the HTTP request.
        json.JSONDecodeError: If the response data is not valid JSON.
    """

    url = f'/repos/{owner}/{repo}/contents/{path}'
    connection = http.client.HTTPSConnection("api.github.com",context=ssl._create_unverified_context())

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Python-http.client"
    }

    if token:
        headers["Authorization"] = f'token {token}'

    connection.request("GET", url, headers=headers)

    response = connection.getresponse()

    data = response.read()

    connection.close()

    files = json.loads(data)

    return files


def get_resource_label(typ):
    return "".join(typ.split("::"))


def get_supported_resource_types():
    owner = "awslabs"
    repo = "aws-config-resource-schema"
    path = "config/properties/resource-types"

    files = get_repo_files(owner, repo, path)

    for file in files:
        fn = file["name"]
        if fn.endswith(".properties.json"):
            yield fn.split(".", 1)[0]


def create_node_constraint(driver: Driver, label: str, property: str):
    """
    Creates a unique constraint on a specified label and property in a Neo4j database.

    Refer to neomodel/sync_/core.py -> _create_node_constraint .

    Support neo4j version 5.x .

    Args:
        driver (Driver): The Neo4j database driver.
        label (str): The label of the node to apply the constraint to.
        property (str): The property of the node that should be unique.

    Raises:
        ClientError: If there is an error executing the query and it is not due to the constraint already existing.
    """
    constraint_name = f"constraint_unique_{label}_{property}"

    try:
        driver.execute_query(
            f"""CREATE CONSTRAINT {constraint_name}
                        FOR (n:{label}) REQUIRE n.{property} IS UNIQUE"""
        )
    except ClientError as e:
        if e.code in (
            RULE_ALREADY_EXISTS,
            CONSTRAINT_ALREADY_EXISTS,
        ):
            print(f'{str(e)}\n')
        else:
            raise


PRIMARY_KEY = "resourceId"


def generate_neo4j_types(driver: Driver):
    types = []

    for resource_type in get_supported_resource_types():
        types.append(resource_type)
        label = get_resource_label(resource_type)
        create_node_constraint(driver, label, PRIMARY_KEY)

    with open("resource-types.json", "w") as f:
        json.dump(types, f, indent=2)


if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(
        description="Generate Neo4j types for AWS Config resources.",
        formatter_class=ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "neo4j_uri",
        type=str,
        help="The URI of the Neo4j database.",
    )

    parser.add_argument(
        "--output",
        type=str,
        dest="output_file",
        default="resource-types.json",
        help="The output file to write the generated types to.",
    )

    parser.add_argument(
        "--username",
        type=str,
        dest="username",
        default="neo4j",
        help="The username to connect to the Neo4j database.",
    )

    parser.add_argument(
        "--password",
        type=str,
        dest="password",
        default="neo4j",
        help="The password to connect to the Neo4j database.",
    )

    args = parser.parse_args()

    driver = GraphDatabase.driver(
        args.neo4j_uri, auth=(args.username, args.password))

    generate_neo4j_types(driver)

    driver.close()
