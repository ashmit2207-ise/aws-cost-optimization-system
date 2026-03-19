import json
import boto3
from datetime import datetime

# Initialize AWS clients
ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:195199692712:cost-monitor-alerts'

def lambda_handler(event, context):
    """
    Check for unattached EBS volumes and calculate cost
    """
    
    print(f"🔍 Starting EBS volume check at {datetime.now()}")
    
    try:
        # Get all EBS volumes
        response = ec2_client.describe_volumes()
        
        unattached_volumes = []
        total_monthly_cost = 0
        
        # Cost per GB per month by volume type
        cost_per_gb = {
            'gp3': 0.08,
            'gp2': 0.10,
            'io1': 0.125,
            'io2': 0.125,
            'st1': 0.045,
            'sc1': 0.025,
            'standard': 0.05
        }
        
        # Check each volume
        for volume in response['Volumes']:
            volume_id = volume['VolumeId']
            size_gb = volume['Size']
            state = volume['State']
            volume_type = volume['VolumeType']
            az = volume['AvailabilityZone']
            attachments = volume['Attachments']
            
            # Volume is unattached if state is 'available' or no attachments
            if state == 'available' or len(attachments) == 0:
                
                # Calculate monthly cost
                price = cost_per_gb.get(volume_type, 0.08)
                monthly_cost = size_gb * price
                total_monthly_cost += monthly_cost
                
                # Get creation time
                create_time = volume.get('CreateTime', 'Unknown')
                if create_time != 'Unknown':
                    age_days = (datetime.now(create_time.tzinfo) - create_time).days
                else:
                    age_days = 0
                
                volume_info = {
                    'VolumeId': volume_id,
                    'Size': f"{size_gb} GB",
                    'Type': volume_type,
                    'State': state,
                    'AZ': az,
                    'Age': f"{age_days} days",
                    'MonthlyCost': f"${monthly_cost:.2f}"
                }
                
                unattached_volumes.append(volume_info)
                print(f"📦 Found: {volume_id} ({size_gb}GB) - ${monthly_cost:.2f}/month")
        
        # Send notification
        if unattached_volumes:
            # Found waste - send alert
            message = f"""
🚨 AWS COST ALERT - Unattached EBS Volumes Found!

Region: {ec2_client.meta.region_name}
Total Volumes: {len(unattached_volumes)}
Monthly Waste: ${total_monthly_cost:.2f}
Annual Waste: ${total_monthly_cost * 12:.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DETAILED BREAKDOWN:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            for idx, vol in enumerate(unattached_volumes, 1):
                message += f"""
{idx}. Volume ID: {vol['VolumeId']}
   Size: {vol['Size']}
   Type: {vol['Type']}
   Age: {vol['Age']}
   Monthly Cost: {vol['MonthlyCost']}
   ───────────────────────────────────
"""
            
            message += f"""
💡 RECOMMENDED ACTION:
Review and delete unnecessary volumes to save ${total_monthly_cost:.2f}/month

  Only delete volumes you don't need!

Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f'💰 Cost Alert: ${total_monthly_cost:.2f}/month Waste',
                Message=message
            )
            
            print(f"📧 Alert sent! {len(unattached_volumes)} volumes")
            
        else:
            # All clear
            message = f"""
✅ AWS COST CHECK - No Unattached EBS Volumes

All volumes are attached. No waste detected!

Checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='✅ Cost Check: All Clear',
                Message=message
            )
            
            print("✅ No waste found!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'unattached_count': len(unattached_volumes),
                'monthly_cost': f"${total_monthly_cost:.2f}"
            })
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='❌ Cost Monitor Error',
            Message=f'Error:\n\n{str(e)}'
        )
        
        raise e
