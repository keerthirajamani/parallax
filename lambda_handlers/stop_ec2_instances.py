import boto3

ec2 = boto3.client('ec2')

def lambda_handler(event, context):

    # Get all running instances
    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
        ]
    )

    instance_ids = []

    # Collect instance IDs
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_ids.append(instance['InstanceId'])

    # Stop instances if any are running
    if instance_ids:
        ec2.stop_instances(InstanceIds=instance_ids)
        print("Stopping instances:", instance_ids)
    else:
        print("No running instances found")

    return instance_ids