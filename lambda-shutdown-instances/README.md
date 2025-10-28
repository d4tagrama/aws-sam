# EC2 Shutdown Automation with AWS SAM

This project provides a serverless solution to automatically stop EC2 instances based on assigned AWS tags. It uses an AWS Lambda function triggered by an Amazon EventBridge (CloudWatch Events) schedule and sends notifications via Amazon SNS.

## 🏗 Architecture Overview

The stack deploys the following components:

| Resource | Description |
|---------|-------------|
| **AWS Lambda Function** | Executes the logic to identify and stop EC2 instances using AWS tags |
| **Amazon SNS Topic** | Used to send an email notification every time the Lambda runs |
| **SNS Subscription** | Email subscription to receive shutdown notifications |
| **EventBridge Rule** | Scheduled trigger for the Lambda and SNS topic |

All components are deployed using the **AWS Serverless Application Model (SAM)**.

---

## ⚙ Environment Variables

The Lambda function includes an environment variable:

| Variable | Usage |
|---------|-------|
| `DRYRUN` | `"True"` means EC2 instances will not actually stop (safe testing). Set `"False"` for real execution |

Example to disable dry run:

```bash
sam deploy --parameter-overrides DRYRUN=False
