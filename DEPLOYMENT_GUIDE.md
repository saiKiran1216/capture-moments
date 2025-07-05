# Capture Moments - AWS Deployment Guide

## Prerequisites
- AWS Account with proper permissions
- GitHub Account
- Git installed on your machine
- AWS CLI installed

## Step 1: GitHub Repository Setup

### 1.1 Create GitHub Repository
1. Go to [GitHub.com](https://github.com) and sign in
2. Click "New repository"
3. Repository name: `capturemoments`
4. Make it Public or Private (your choice)
5. **Don't** initialize with README (we already have files)
6. Click "Create repository"

### 1.2 Upload Code to GitHub
After creating the repository, run these commands:

```bash
# Add remote origin (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/capturemoments.git

# Push to GitHub
git push -u origin main
```

## Step 2: AWS Setup

### 2.1 Get AWS Credentials
1. Go to AWS Console → IAM → Users → Your username
2. Click "Security credentials" tab
3. Click "Create access key"
4. Choose "Command Line Interface (CLI)"
5. Download the .csv file with your credentials

### 2.2 Configure AWS CLI
```bash
aws configure
# Enter your Access Key ID
# Enter your Secret Access Key
# Enter region: ap-south-1
# Enter output format: json
```

### 2.3 Test AWS Setup
```bash
python setup_aws.py
```

## Step 3: Create EC2 Instance

### 3.1 Launch Instance
1. Go to AWS Console → EC2
2. Click "Launch Instance"
3. Configure:
   - **Name**: CaptureMoments-Instance
   - **AMI**: Amazon Linux 2 (Free tier eligible)
   - **Instance type**: t2.micro
   - **Key pair**: Create new key pair
   - **Download the .pem file** and save it in your project folder

### 3.2 Configure Security Group
1. In Network settings, click "Edit"
2. Add these rules:
   - **SSH (22)**: Source 0.0.0.0/0
   - **Custom TCP (5000)**: Source 0.0.0.0/0
   - **HTTP (80)**: Source 0.0.0.0/0 (optional)

### 3.3 Launch and Get Public IP
1. Click "Launch Instance"
2. Wait for instance to be running
3. Copy the **Public IPv4 address**

## Step 4: Create IAM Role

### 4.1 Create Role
1. Go to AWS Console → IAM → Roles
2. Click "Create Role"
3. Select:
   - **Trusted entity**: AWS service
   - **Use case**: EC2
4. Attach permissions:
   - Search for "AmazonDynamoDBFullAccess"
   - Check the box
5. Name: `EC2DynamoDBAccessRole`
6. Create the role

### 4.2 Attach Role to EC2
1. Go back to EC2 → Instances
2. Select your instance
3. Actions → Security → Modify IAM role
4. Attach: `EC2DynamoDBAccessRole`

## Step 5: Create DynamoDB Tables

### 5.1 Run Setup Script
```bash
python deploy_aws.py
```

This will create:
- `photographers` table (partition key: photographer_id)
- `booking` table (partition key: booking_id)

## Step 6: Deploy to EC2

### 6.1 Connect to EC2
1. Move your .pem file to the project folder
2. Open Git Bash
3. Navigate to your project folder
4. Connect using the command from EC2 console:
```bash
ssh -i "your-key.pem" ec2-user@YOUR_PUBLIC_IP
```

### 6.2 Install Dependencies
```bash
# Update system
sudo yum update -y

# Install Python and Git
sudo yum install python3 git -y

# Install Python packages
pip3 install --user flask boto3

# Clone your repository
git clone https://github.com/YOUR_USERNAME/capturemoments.git

# Navigate to project
cd capturemoments
```

### 6.3 Run the Application
```bash
# Run the Flask app
python3 awsint.py
```

### 6.4 Access Your Website
Open your browser and go to:
```
http://YOUR_PUBLIC_IP:5000
```

## Step 7: Update Application

When you make changes to your code:

1. **Update GitHub**:
```bash
git add .
git commit -m "Your commit message"
git push origin main
```

2. **Update EC2**:
```bash
# Stop the Flask app (Ctrl+C)
git pull origin main
python3 awsint.py
```

## Troubleshooting

### Common Issues:

1. **"Unable to locate credentials"**
   - Run `aws configure` and enter your credentials

2. **"Permission denied" when connecting to EC2**
   - Make sure your .pem file has correct permissions
   - Use: `chmod 400 your-key.pem`

3. **"Port 5000 not accessible"**
   - Check EC2 security group allows port 5000
   - Verify the Flask app is running

4. **"DynamoDB table not found"**
   - Run `python setup_aws.py` to create tables
   - Check IAM role has DynamoDB permissions

### Useful Commands:

```bash
# Check AWS credentials
aws sts get-caller-identity

# List DynamoDB tables
aws dynamodb list-tables --region ap-south-1

# Check EC2 instance status
aws ec2 describe-instances --instance-ids YOUR_INSTANCE_ID
```

## Security Notes

- Keep your .pem file secure
- Don't commit AWS credentials to GitHub
- Consider using AWS Secrets Manager for production
- Regularly update your EC2 instance

## Cost Optimization

- Use t2.micro for free tier
- Stop EC2 instance when not in use
- Monitor DynamoDB usage
- Set up billing alerts

---

**Your Capture Moments application should now be successfully deployed on AWS!** 