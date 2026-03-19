import json
import boto3
from datetime import datetime, timezone

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:195199692712:cost-monitor-alerts'

def lambda_handler(event, context):
    print(f"Starting snapshot check at {datetime.now()}")
    
    try:
        response = ec2_client.describe_snapshots(OwnerIds=['self'])
        old_snapshots = []
        total_monthly_cost = 0
        snapshot_price_per_gb = 0.05
        old_days_threshold = 90
        
        for snapshot in response['Snapshots']:
            snapshot_id = snapshot['SnapshotId']
            size_gb = snapshot['VolumeSize']
            start_time = snapshot['StartTime']
            description = snapshot.get('Description', 'No description')
            
            age_days = (datetime.now(timezone.utc) - start_time).days
            
            if age_days > old_days_threshold:
                monthly_cost = size_gb * snapshot_price_per_gb
                total_monthly_cost += monthly_cost
                
                snapshot_info = {
                    'SnapshotId': snapshot_id,
                    'Size': f"{size_gb} GB",
                    'Age': f"{age_days} days",
                    'Created': start_time.strftime('%Y-%m-%d'),
                    'MonthlyCost': f"${monthly_cost:.2f}"
                }
                
                old_snapshots.append(snapshot_info)
                print(f"Found old snapshot: {snapshot_id} - {age_days} days - ${monthly_cost:.2f}/month")
        
        if old_snapshots:
            message = f"AWS COST ALERT - Old EBS Snapshots\n\n"
            message += f"Region: {ec2_client.meta.region_name}\n"
            message += f"Old Snapshots (>{old_days_threshold} days): {len(old_snapshots)}\n"
            message += f"Monthly Waste: ${total_monthly_cost:.2f}\n"
            message += f"Annual Waste: ${total_monthly_cost * 12:.2f}\n\n"
            
            for idx, snap in enumerate(old_snapshots, 1):
                message += f"{idx}. {snap['SnapshotId']}\n"
                message += f"   Size: {snap['Size']}, Age: {snap['Age']}\n"
                message += f"   Created: {snap['Created']}\n"
                message += f"   Cost: {snap['MonthlyCost']}/month\n\n"
            
            message += f"\nReview and delete old snapshots to save ${total_monthly_cost:.2f}/month"
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Cost Alert: ${total_monthly_cost:.2f}/month in Old Snapshots",
                Message=message
            )
            print(f"Alert sent! Found {len(old_snapshots)} old snapshots")
        else:
            message = "AWS COST CHECK - No Old Snapshots\n\n"
            message += f"No snapshots older than {old_days_threshold} days found."
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Cost Check: No Old Snapshots",
                Message=message
            )
            print("No old snapshots found!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'old_snapshots_count': len(old_snapshots),
                'monthly_cost': f"${total_monthly_cost:.2f}"
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Cost Monitor Error - Snapshots",
            Message=f"Error: {str(e)}"
        )
        raise e
