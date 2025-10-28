import os
import json

# import requests
import boto3 # type: ignore
from botocore.exceptions import ClientError, BotoCoreError # type: ignore

import logging

logger = logging.getLogger()
SHUTDOWN_TAG_NAME = os.environ.get('SHUTDOWN_TAG_NAME', 'SHUTDOWN')
SHUTDOWN_TAG_VALUE = os.environ.get('SHUTDOWN_TAG_VALUE', 'Yes')
MAX_INSTANCES_PER_CALL = 100  # AWS limit


client = boto3.client('ec2')
def get_instances():
    try:
        response = client.describe_instances(
            Filters=[
                    {
                        'Name': f'tag:{SHUTDOWN_TAG_NAME}',
                        'Values': [SHUTDOWN_TAG_VALUE]
                    },
                    {
                        'Name': 'instance-state-name',
                        'Values': ['running']
                    }
            ]
        )
        instances_on= []
        for reservations in response.get("Reservations",[]):
            for instance in reservations.get("Instances", []):
                instances_on.append({
                    "InstanceId": instance.get("InstanceId"),
                    "State": instance.get("State", {}).get("Name"),
                    "InstanceType": instance.get("InstanceType"),
                    "PrivateIpAddress": instance.get("PrivateIpAddress"),
                    "PublicIpAddress": instance.get("PublicIpAddress"),
                    "Tags": instance.get("Tags", [])
                })
        logger.info(f"Found {len(instances_on)} running instances tagged for shutdown")
        return instances_on
    except ClientError as e:
        logger.error(f"AWS API error while describing instances: {e.response['Error']['Code']}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while describing instances: {str(e)}")
        raise

def shutdown_ec2(instances,dry_run=True):
    if not instances:
        logger.info("No instances to shutdown")
        return {"StoppedInstances": []}
    instance_ids = [inst["InstanceId"] for inst in instances]
    if len(instance_ids) > MAX_INSTANCES_PER_CALL:
        logger.warning(f"Attempting to stop {len(instance_ids)} instances, which exceeds AWS limit of {MAX_INSTANCES_PER_CALL}")
        instance_ids = instance_ids[:MAX_INSTANCES_PER_CALL]
    try:
        response = client.stop_instances(
            InstanceIds=instance_ids,
            DryRun=dry_run
        )
        logger.info(f"Successfully stopped {len(instance_ids)} instances")
        return response
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'DryRunOperation':
            logger.info(f"DryRun: Would have stopped {len(instance_ids)} instances")
            return {
                "DryRun": True,
                "InstanceIds": instance_ids,
                "Message": "DryRun successful - instances would be stopped"
            }
        else:
            logger.error(f"Failed to stop instances: {e.response['Error']['Code']} - {e.response['Error']['Message']}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error while stopping instances: {str(e)}")
        raise
def lambda_handler(event, context):
    try:
        enable_dry_run = os.environ.get('DRYRUN', "True")  # Default to True for safety
        dry_run = enable_dry_run.lower() in ("true", "1", "yes")
        
        logger.info(f"Starting EC2 shutdown Lambda (DryRun: {dry_run})")
        
        instances_on = get_instances()
        shutdown_response = shutdown_ec2(instances_on, dry_run)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "instanceCount": len(instances_on),
                "dryRun": dry_run,
                "instanceIds": [inst["InstanceId"] for inst in instances_on]
            })
        }
        
    except ClientError as e:
        logger.error(f"AWS error: {e.response['Error']['Code']}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": "AWS API error",
                "errorCode": e.response['Error']['Code']
            })
        }
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "error": "Internal error"
            })
        }