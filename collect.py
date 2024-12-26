import os

import json
import re
import gzip

from datetime import datetime, timedelta, timezone

from mypy_boto3_s3.client import S3Client
from mypy_boto3_config import ConfigServiceClient
from mypy_boto3_config.type_defs import ResourceFiltersTypeDef

from merge import merge_item

BOTO_DATE_FORMAT = r"%Y-%m-%dT%H:%M:%S.000Z"


class FileCollector(object):
    def __init__(self, driver):
        self.driver = driver

    def parse(self, f):
        data = json.load(f)

        for item in data['configurationItems']:
            try:
                merge_item(driver=self.driver, item=item)
            except Exception as e:
                print(f'Error: {e} , item: {item}')


class S3Collector(FileCollector):
    def __init__(self, client: S3Client, driver, bucket, prefix="", pattern=r".*ConfigSnapshot.*\.json\.gz$", last_modified=datetime.now(timezone.utc) - timedelta(hours=24), storage_classes=("STANDARD", "STANDARD_IA", "REDUCED_REDUNDANCY")):
        super().__init__(driver)
        self.client = client
        self.bucket = bucket
        self.prefix = prefix
        self.pattern = re.compile(pattern)

        self.last_modified = last_modified
        self.storage_classes = storage_classes

    def get_keys(self):
        """
        Generator function to retrieve keys from an S3 bucket.

        This function uses a paginator to iterate through the objects in an S3 bucket
        and yields each key that meets the specified criteria. It also provides warnings
        when a large number of keys have been scanned.

        Refer to splunk_ta_aws generic_s3 -> get_keys

        Yields:
            dict: A dictionary representing an S3 object key.

        Raises:
            None

        Notes:
            - The function will print a warning message after every 1 million keys scanned.
            - Keys are filtered based on the last modified date and storage class if specified.

        Attributes:
            self.client (boto3.client): The boto3 client for S3.
            self.bucket (str): The name of the S3 bucket.
            self.prefix (str): The prefix to filter the S3 objects.
            self.last_modified (str): The last modified date to filter the S3 objects.
            self.storage_classes (list): The list of storage classes to filter the S3 objects.
        """
        scanned_keys = 0
        total_scanned_keys = 0
        for page in self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket,
            Prefix=self.prefix
        ):
            for key in page.get("Contents", []):
                total_scanned_keys += 1
                scanned_keys += 1

                # Warning for the skipped keys when 1 million keys are scanned
                if scanned_keys == 1000000:
                    print(
                        f"Scan is in progress. {scanned_keys} keys are scanned. Amazon S3 bucket with an excessive "
                        "number of files or abundant size will result in significant performance degradation and "
                        "ingestion delays. It is recommended to use SQS-Based S3 input instead of Generic S3 to ingest "
                        "the Amazon S3 bucket data."
                    )
                    scanned_keys = 0

                key_last_modified = key["LastModified"]

                if (not self.last_modified) or (key_last_modified >= self.last_modified):
                    if self.storage_classes and key["StorageClass"] not in self.storage_classes:
                        print(
                            "Skipped this key because storage class does not match"
                            "(only supports STANDARD, STANDARD_IA and REDUCED_REDUNDANCY).",
                            key_name=key["Key"],
                            storage_class=key["StorageClass"],
                        )
                        continue

                    if self.pattern.match(key["Key"]):
                        yield key

    def collect(self):
        for key in self.get_keys():
            try:
                res = self.client.get_object(
                    Bucket=self.bucket, Key=key["Key"])
                with gzip.open(res['Body'], 'rt') as f:
                    self.parse(f)
            except Exception as e:
                print(f'Error: {e} , key: {key["Key"]}')


class LocalCollector(FileCollector):
    def __init__(self, driver, path: str):
        super().__init__(driver)
        self.path = path

    def collect(self):
        for fn in os.listdir(self.path):
            if fn.endswith(".json"):
                with open(os.path.join(self.path, fn)) as f:
                    self.parse(f)


class APICollector(object):
    def __init__(self, client: ConfigServiceClient, driver, name="default", is_aggregator=True, resource_types=["AWS::EC2::Instance"]):
        self.client = client
        self.driver = driver
        self.name = name
        self.is_aggregator = is_aggregator
        if resource_types is None or len(resource_types) == 0:
            with open("resource-types.json", "r") as f:
                self.resource_types = json.load(f)
        else:
            self.resource_types = resource_types

    def collect(self, filter: ResourceFiltersTypeDef = {}):
        for resource_type in self.resource_types:
            if self.is_aggregator:
                for page in self.client.get_paginator("list_aggregate_discovered_resources").paginate(
                    ConfigurationAggregatorName=self.name,
                    ResourceType=resource_type,
                    Filters=filter
                ):
                    # resp = self.client.batch_get_aggregate_resource_config(
                    #     ConfigurationAggregatorName=self.name,
                    #     ResourceIdentifiers=page["ResourceIdentifiers"]
                    # )

                    # for item in resp["BaseConfigurationItems"]:
                    #     merge_item(driver=self.driver, item=item)

                    for item in page["ResourceIdentifiers"]:
                        resp = self.client.get_aggregate_resource_config(
                            ConfigurationAggregatorName=self.name,
                            ResourceIdentifier=item
                        )
                        merge_item(driver=self.driver, item=resp["ConfigurationItem"])

            else:
                for page in self.client.get_paginator("list_discovered_resources").paginate(
                    resourceType=resource_type
                ):
                    resp = self.client.batch_get_resource_config(
                        resourceKeys=[{"resourceId": item["resourceId"], "resourceType": item["resourceType"]}
                                      for item in page["resourceIdentifiers"]]
                    )
                    for item in resp["baseConfigurationItems"]:
                        merge_item(driver=self.driver, item=item)
