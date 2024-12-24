# AWS Config Resource Collector

A tool for collecting AWS Config resources and storing them in Neo4j graph database.

## Features

- Multiple collection methods:
  - S3: Collect from AWS Config snapshots stored in S3
  - Local: Collect from local JSON files
  - API: Collect directly from AWS Config API
- Scheduled collection support
- Docker containerized deployment
- Support for AWS Config Aggregator
- Relationship mapping between resources

## Prerequisites

- Python 3.9+
- Neo4j 5.x
- AWS credentials configured
- Docker and Docker Compose (for containerized deployment)

## Installation

### Local Development

1. Create virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```
2. Configure AWS credentials:
```bash
aws configure
```

### Docker Deployment

1. Create `.env` file with required variables:
```bash
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
BUCKET_NAME=your-config-bucket
```

2. Start services using docker-compose:
```bash
docker-compose up -d
```

## Usage

### Command Line Interface

1. Initialize Neo4j indexes:

```bash:README.md
python index.py bolt://localhost:7687 --username neo4j --password your_password
```

2. Collect resources:

- From S3:

```bash
python main.py --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password your_password s3 your-bucket --prefix config/
```

- From local files:
```bash
python main.py --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password your_password local /path/to/config/files
```

- From AWS Config API:
```bash
python main.py --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password your_password api --aggregator-name your-aggregator
```

3. Schedule daily collection:
```bash
python main.py --command schedule --neo4j-uri bolt://localhost:7687 --neo4j-user neo4j --neo4j-password your_password --schedule-time "02:00" s3 your-bucket
```

## AWS Config Setup

### How to collect multi accounts' resources in single account
#### Collect resources in a config aggregator
[Creating Aggregators for AWS Config
](https://docs.aws.amazon.com/config/latest/developerguide/aggregated-create.html)

#### Delivery configuration snapshots to a single bucket
Just set all config recorder delivery configuration to a single bucket.

And set the bucket permissions, refer to [Permissions for the Amazon S3 Bucket for the AWS Config Delivery Channel](https://docs.aws.amazon.com/config/latest/developerguide/s3-bucket-policy.html) .

You can add all accounts to the `AWS:SourceAccount` or use `aws:SourceOrgID` .

### How to enable AWS Config Recorder in multiple accounts and regions

#### AWS SSM quick setup
[Create an AWS Config configuration recorder using Quick Setup](https://docs.aws.amazon.com/systems-manager/latest/userguide/quick-setup-config.html)

However, `Quick Setup` does not support in the follow regions:
```
Europe (Milan)

Asia Pacific (Hong Kong)

Middle East (Bahrain)

China (Beijing)

China (Ningxia)

AWS GovCloud (US-East)

AWS GovCloud (US-West)
```

#### CloudFormation StackSet(Recommended)
[my-awsconfig-stackset walkthrough](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-getting-started-create.html)

#### Use boto3
[aws-config-enable](https://github.com/wanmail/aws-config-enable)

## Project Structure

- `main.py`: Main entry point and CLI interface
- `collect.py`: Resource collection implementations
- `merge.py`: Neo4j data merging logic
- `index.py`: Neo4j index initialization
- `args.py`: Command line argument parsing
- `docker-compose.yml`: Docker services configuration
- `Dockerfile`: Container build configuration

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

