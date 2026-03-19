import json
import boto3
from datetime import datetime

ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:195199692712:cost-monitor-alerts'

def lambda_handler(event, context):
    print(f"Starting Elastic IP check at {datetime.now()}")
    
    try:
        response = ec2_client.describe_addresses()
        unassociated_eips = []
        eip_monthly_cost = 3.60
        total_monthly_cost = 0
        
        for address in response['Addresses']:
            allocation_id = address.get('AllocationId', 'N/A')
            public_ip = address.get('PublicIp', 'Unknown')
            association_id = address.get('AssociationId', None)
            instance_id = address.get('InstanceId', None)
            
            if not association_id and not instance_id:
                total_monthly_cost += eip_monthly_cost
                
                eip_info = {
                    'AllocationId': allocation_id,
                    'PublicIP': public_ip,
                    'MonthlyCost': f"${eip_monthly_cost:.2f}"
                }
                
                unassociated_eips.append(eip_info)
                print(f"Found unassociated EIP: {public_ip} - ${eip_monthly_cost:.2f}/month")
        
        if unassociated_eips:
            message = f"AWS COST ALERT - Unassociated Elastic IPs\n\n"
            message += f"Region: {ec2_client.meta.region_name}\n"
            message += f"Unassociated IPs: {len(unassociated_eips)}\n"
            message += f"Monthly Waste: ${total_monthly_cost:.2f}\n"
            message += f"Annual Waste: ${total_monthly_cost * 12:.2f}\n\n"
            
            for idx, eip in enumerate(unassociated_eips, 1):
                message += f"{idx}. IP: {eip['PublicIP']}\n"
                message += f"   Allocation ID: {eip['AllocationId']}\n"
                message += f"   Cost: {eip['MonthlyCost']}/month\n\n"
            
            message += f"\nRelease unused Elastic IPs to save ${total_monthly_cost:.2f}/month"
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f"Cost Alert: ${total_monthly_cost:.2f}/month in Elastic IPs",
                Message=message
            )
            print(f"Alert sent! Found {len(unassociated_eips)} unassociated IPs")
        else:
            message = "AWS COST CHECK - No Unassociated Elastic IPs\n\n"
            message += "All Elastic IPs are associated with instances."
            
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Cost Check: No Unassociated IPs",
                Message=message
            )
            print("No unassociated IPs found!")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'unassociated_count': len(unassociated_eips),
                'monthly_cost': f"${total_monthly_cost:.2f}"
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject="Cost Monitor Error - Elastic IPs",
            Message=f"Error: {str(e)}"
        )
        raise e
