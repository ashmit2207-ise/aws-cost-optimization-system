import json
import boto3
from datetime import datetime

lambda_client = boto3.client('lambda')
sns_client = boto3.client('sns')

SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:195199692712:cost-monitor-alerts'

CHECKER_FUNCTIONS = [
      'costmonitor-EBS-checker',
    'costmonitor-snapshot-check',
    'costmonitor-EIP-checker',
    'costmonitor-EC2-checker'
]

def lambda_handler(event, context):
    print(f"Starting daily cost monitoring at {datetime.now()}")
    
    results = []
    total_issues = 0
    
    try:
        for function_name in CHECKER_FUNCTIONS:
            print(f"Invoking {function_name}...")
            
            try:
                response = lambda_client.invoke(
                    FunctionName=function_name,
                    InvocationType='RequestResponse'
                )
                
                payload = json.loads(response['Payload'].read())
                
                if response['StatusCode'] == 200:
                    body = json.loads(payload.get('body', '{}'))
                    
                    checker_type = function_name.replace('CostMonitor-', '').replace('-Checker', '')
                    
                    result = {
                        'checker': checker_type,
                        'status': 'Success',
                        'data': body
                    }
                    
                    results.append(result)
                    
                    count_key = None
                    if 'unattached_count' in body:
                        count_key = 'unattached_count'
                    elif 'old_snapshots_count' in body:
                        count_key = 'old_snapshots_count'
                    elif 'unassociated_count' in body:
                        count_key = 'unassociated_count'
                    elif 'stopped_instances_count' in body:
                        count_key = 'stopped_instances_count'
                    
                    if count_key:
                        total_issues += body.get(count_key, 0)
                    
                    print(f"✅ {function_name} completed: {body}")
                else:
                    print(f"❌ {function_name} failed with status {response['StatusCode']}")
                    results.append({
                        'checker': function_name,
                        'status': 'Failed',
                        'error': f"Status code: {response['StatusCode']}"
                    })
                    
            except Exception as e:
                print(f"❌ Error invoking {function_name}: {str(e)}")
                results.append({
                    'checker': function_name,
                    'status': 'Error',
                    'error': str(e)
                })
        
        summary_message = f"""
AWS COST MONITORING - DAILY SUMMARY
{'='*50}

Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Region: {lambda_client.meta.region_name}

CHECKS COMPLETED:
"""
        
        for result in results:
            summary_message += f"\n{result['checker']}:\n"
            if result['status'] == 'Success':
                data = result['data']
                summary_message += f"  Status: ✅ Success\n"
                summary_message += f"  Cost: {data.get('monthly_cost', 'N/A')}\n"
            else:
                summary_message += f"  Status: ❌ {result['status']}\n"
                summary_message += f"  Error: {result.get('error', 'Unknown')}\n"
        
        summary_message += f"\n{'='*50}\n"
        summary_message += f"Total Issues Found: {total_issues}\n"
        summary_message += f"\nIndividual alerts have been sent for each check.\n"
        summary_message += f"Check your email for detailed reports.\n"
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f'Daily Cost Monitoring Summary - {total_issues} Issues Found',
            Message=summary_message
        )
        
        print("✅ All checks completed!")
        print(f"Summary: {total_issues} total issues found")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily cost monitoring completed',
                'total_issues': total_issues,
                'results': results
            })
        }
        
    except Exception as e:
        error_msg = f"Orchestrator error: {str(e)}"
        print(f"❌ {error_msg}")
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='Cost Monitor - Orchestrator Error',
            Message=f'Error running daily cost checks:\n\n{str(e)}'
        )
        
        raise e
