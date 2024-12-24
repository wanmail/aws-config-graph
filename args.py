import argparse
from neo4j import GraphDatabase
import boto3

from collect import S3Collector, LocalCollector, APICollector

def create_parser():
    parser = argparse.ArgumentParser(
        description="AWS Config Resource Collector",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Neo4j connection parameters
    parser.add_argument(
        "--neo4j-uri",
        type=str,
        default="bolt://localhost:7687",
        help="Neo4j connection URI"
    )
    parser.add_argument(
        "--neo4j-user",
        type=str,
        default="neo4j",
        help="Neo4j username"
    )
    parser.add_argument(
        "--neo4j-password",
        type=str,
        default="neo4j",
        help="Neo4j password"
    )

    # AWS credentials
    parser.add_argument(
        "--profile",
        type=str,
        help="AWS profile name"
    )
    parser.add_argument(
        "--region",
        type=str,
        default="us-east-1",
        help="AWS region name"
    )
    
    # Schedule parser
    parser.add_argument(
        '--command',
        type=str,
        default='run',
        choices=['run', 'schedule'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--schedule-time',
        type=str,
        default="00:00",
        help="Daily schedule time in HH:MM format"
    )
    
    collector_subparsers = parser.add_subparsers(
        dest='collector_type', 
        help='Type of collector to use'
    )

    # S3 collector arguments
    s3_parser = collector_subparsers.add_parser('s3', help='Collect from S3 bucket')
    s3_parser.add_argument('bucket', type=str, help='S3 bucket name')
    s3_parser.add_argument('--prefix', type=str, default='', help='S3 bucket prefix')
    s3_parser.add_argument('--pattern', type=str, default=r'.*\.json\.gz$', help='File pattern to match')
    s3_parser.add_argument('--last-modified', type=str, help='Filter by last modified date (YYYY-MM-DDThh:mm:ss.000Z)')

    # Local collector arguments
    local_parser = collector_subparsers.add_parser('local', help='Collect from local directory')
    local_parser.add_argument('path', type=str, help='Local directory path')

    # API collector arguments
    api_parser = collector_subparsers.add_parser('api', help='Collect from AWS Config API')
    api_parser.add_argument('--aggregator-name', type=str, default='default', help='Config Aggregator name')
    api_parser.add_argument('--no-aggregator', action='store_true', help='Disable aggregator mode')
    api_parser.add_argument('--resource-types', nargs='+', help='List of resource types to collect')
    api_parser.add_argument('--filter-region', type=str, help='Filter resources by region')

    return parser 


def run(args):
        # Initialize Neo4j driver
    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password)
    )

    # Initialize AWS session
    session_kwargs = {}
    if args.profile:
        session_kwargs['profile_name'] = args.profile
    session = boto3.session.Session(**session_kwargs)

    if args.collector_type == 's3':
        # Initialize S3 collector
        s3_client = session.client('s3')
        collector = S3Collector(
            client=s3_client,
            driver=driver,
            bucket=args.bucket,
            prefix=args.prefix,
            pattern=args.pattern,
            last_modified=args.last_modified
        )

    elif args.collector_type == 'local':
        # Initialize Local collector
        collector = LocalCollector(
            driver=driver,
            path=args.path
        )

    elif args.collector_type == 'api':
        # Initialize API collector
        config_client = session.client('config', region_name=args.region)
        filter_args = {}
        if args.filter_region:
            filter_args['Region'] = args.filter_region

        collector = APICollector(
            client=config_client,
            driver=driver,
            name=args.aggregator_name,
            is_aggregator=not args.no_aggregator,
            resource_types=args.resource_types
        )
        collector.collect(filter=filter_args)
        return

    else:
        raise ValueError(f'Unknown collector type: {args.collector_type}')

    # Run collection
    collector.collect()
    
    driver.close()