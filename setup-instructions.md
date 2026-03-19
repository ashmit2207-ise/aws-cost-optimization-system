# ⚙️ Setup Instructions

## 📌 Project Overview
This project is an **Automated AWS Cost Monitoring System** built using serverless architecture that detects unused resources and sends daily email alerts.

---

## ✅ Prerequisites

- AWS Account
- Basic understanding of AWS services (Lambda, EventBridge, SNS)

---

## 🔐 Configure IAM Role

1. Create an IAM role for Lambda  
2. Attach permissions:
   - AmazonEC2ReadOnlyAccess  
   - AmazonSNSFullAccess  

---

## ⚙️ Create Lambda Function

1. Go to AWS Lambda  
2. Create a new function  
3. Upload your project code (ZIP or inline)  
4. Set runtime as Python  

---

## ⏰ Configure EventBridge (Scheduler)

1. Go to EventBridge  
2. Create a rule  
3. Set schedule (e.g., daily at 9 AM)  
4. Set target as your Lambda function  

---

## 📧 Setup SNS Notifications

1. Create an SNS topic  
2. Add email subscription  
3. Confirm email subscription  
4. Connect Lambda to SNS  

---

## 📁 Project Structure

- ebs_checker.py → Detects unused EBS volumes  
- snapshot_checker.py → Finds old snapshots  
- eip_checker.py → Identifies unused Elastic IPs  
- ec2_checker.py → Lists stopped EC2 instances  
- orchestrator.py → Runs all checks and sends report  

---

## 📧 Output

- AWS Lambda logs (CloudWatch)  
- Email alerts via SNS  

---

## 🎯 Goal

To automatically identify unused AWS resources and reduce cloud costs using a serverless architecture.
To automatically identify unused AWS resources and reduce cloud costs using a serverless architecture.
