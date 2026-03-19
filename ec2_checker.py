import json
import boto3
from datetime import datetime, timezone

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:195199692712:cost-monitor-alerts'

def lambda_handler(event, context):
    print(f"Starting stopped EC2 check at {datetime.now()}")
    
    try:
        response = ec2_client.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}]
        )
        
        stopped_instances = []
        total_monthly_cost = 0
        stopped_days_threshold = 7
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                launch_time = instance['LaunchTime']
                state_transition = instance.get('StateTransitionReason', '')
                
                stopped_time = None
                if 'User initiated' in state_transition:
                    try:
                        time_part = state_transition.split('(')[1].split(')')[0]
                        stopped_time = datetime.strptime(time_part, '%Y-%m-%d %H:%M:%S %Z')
                        stopped_time = stopped_time.replace(tzinfo=timezone.utc)
                    except:
                        stopped_time = None
                
                if stopped_time:
                    stopped_days = (datetime.now(timezone.utc) - stopped_time).days
                else:
                    stopped_days = 0
                
                ebs_cost = 0
                total_storage_gb = 0
                
                for mapping in instance.get('BlockDeviceMappings', []):
                    if 'Ebs' in mapping:
                        volume_id = mapping['Ebs']['VolumeId']
                        volume = ec2_client.describe_volumes(VolumeIds=[volume_id])['Volumes'][0]
                        size_gb = volume['Size']
                        volume_type = volume['VolumeType']
                        
                        total_storage_gb += size_gb
                        
                        cost_per_gb = {
                            'gp3': 0.08,
                            'gp2': 0.10,
                            'io1': 0.125,
                            'io2': 0.125,
                            'st1': 0.045,
                            'sc1': 0.025,
                            'standard': 0.05
                        }
                        
                        price = cost_per_gb.get(volume_type, 0.08)
                        ebs_cost += size_gb * price
                
                total_monthly_cost += ebs_cost
                
                name_tag = 'N/A'
                for tag in instance.get('Tags', []):
                    if tag['Key'] == 'Name':
                        name_tag = tag['Value']
                        break
                
                instance_info = {
                    'InstanceId': instance_id,
                    'Name': name_tag,
                    'Type': instance_type,
                    'StoppedDays': stopped_days,
                    'StorageGB': f"{total_storage_gb} GB",
                    'MonthlyCost': f"${ebs_cost:.2f}"
                }
                
                if stopped_days >= stopped_days_threshold:
                    stopped_instances.append(instance_info)
                    print(f"Found: {instance_id} stopped {stopped_days} days - ${ebs_cost:.2f}/month")
        
        if stopped_instances:
            message = f"AWS COST ALERT - Stopped EC2 Instances\n\n"
            message += f"Region: {ec2_client.meta.region_name}\n"
            message += f"Stopped instances (>{stopped_days_threshold} days): {len(stopped_instances)}\n"
            message += f"Monthly EBS Cost: ${total_monthly_cost:.2f}\n"
            message += f"Annual EBS Cost: ${total_monthly_cost * 12:.2f}\n\n"
            
            for idx, inst in enumerate(stopped_instances, 1):
                message += f"{idx}. {inst['InstanceId']} ({inst['Name']})\n"
                message += f"   Type: {inst['Type']}\n"
                message += f"   Stopped: {inst['StoppedDays']} days\n"
                message += f"   Storage: {inst['StorageGB']}\n"
                message += f"   EBS Cost: {inst['MonthlyCost']}/month\n\n"
            
            message += f"\nConsider terminating unused instances to save ${total_monthly_cost:.2f}/month"
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Cost Alert: ${total_monthly_cost:.2f}/month in Stopped EC2",
                Message=message
            )
            print(f"Alert sent! Found {len(stopped_instances)} stopped instances")
        else:
            message = "AWS COST CHECK - No Long-Term Stopped EC2 Instances\n\n"
            message += f"No instances stopped longer than {stopped_days_threshold} days."
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Cost Check: No Stopped Instances",
                Message=message
            )
            print("No stopped instances found!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'stopped_instances_count': len(stopped_instances),
                'monthly_cost': f"${total_monthly_cost:.2f}"
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Cost Monitor Error - EC2",
            Message=f"Error: {str(e)}"
        )
        raise e
