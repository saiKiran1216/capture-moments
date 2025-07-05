#!/usr/bin/env python3
"""
Simplified AWS Setup for Capture Moments
This script helps verify AWS configuration and test DynamoDB connection
"""

import boto3
import sys
from botocore.exceptions import ClientError, NoCredentialsError

def check_aws_credentials():
    """Check if AWS credentials are properly configured"""
    try:
        # Try to create a session
        session = boto3.Session()
        sts = session.client('sts')
        
        # Get caller identity to verify credentials
        response = sts.get_caller_identity()
        print(f"✅ AWS Credentials verified!")
        print(f"   Account ID: {response['Account']}")
        print(f"   User ID: {response['UserId']}")
        print(f"   ARN: {response['Arn']}")
        return True
        
    except NoCredentialsError:
        print("❌ AWS credentials not found!")
        print("Please run: aws configure")
        return False
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")
        return False

def test_dynamodb_connection(region_name='ap-south-1'):
    """Test DynamoDB connection and list tables"""
    try:
        dynamodb = boto3.resource('dynamodb', region_name=region_name)
        
        # List tables
        tables = list(dynamodb.tables.all())
        print(f"\n📊 DynamoDB Tables in {region_name}:")
        
        if tables:
            for table in tables:
                print(f"   - {table.name}")
        else:
            print("   No tables found")
            
        return True
        
    except Exception as e:
        print(f"❌ DynamoDB connection failed: {e}")
        return False

def create_tables_if_missing(region_name='ap-south-1'):
    """Create required tables if they don't exist"""
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    
    required_tables = {
        'photographers': {
            'KeySchema': [{'AttributeName': 'photographer_id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'photographer_id', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        'booking': {
            'KeySchema': [{'AttributeName': 'booking_id', 'KeyType': 'HASH'}],
            'AttributeDefinitions': [{'AttributeName': 'booking_id', 'AttributeType': 'S'}],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    }
    
    created_tables = []
    
    for table_name, table_config in required_tables.items():
        try:
            # Check if table exists
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✅ Table '{table_name}' already exists")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                # Create table
                try:
                    table = dynamodb.create_table(
                        TableName=table_name,
                        **table_config
                    )
                    table.wait_until_exists()
                    print(f"✅ Created table '{table_name}'")
                    created_tables.append(table_name)
                except Exception as create_error:
                    print(f"❌ Failed to create table '{table_name}': {create_error}")
    
    return created_tables

def main():
    """Main setup function"""
    print("🚀 AWS Setup for Capture Moments")
    print("=" * 40)
    
    # Check credentials
    if not check_aws_credentials():
        return
    
    # Test DynamoDB connection
    if not test_dynamodb_connection():
        return
    
    # Create tables
    print("\n📊 Creating required tables...")
    created_tables = create_tables_if_missing()
    
    if created_tables:
        print(f"\n✅ Successfully created {len(created_tables)} tables")
    else:
        print("\n✅ All required tables already exist")
    
    print("\n🎉 AWS setup complete!")
    print("\nNext steps:")
    print("1. Create EC2 instance with Amazon Linux 2")
    print("2. Configure security group to allow port 5000")
    print("3. Create IAM role with DynamoDB permissions")
    print("4. Upload your .pem key to the project folder")
    print("5. Connect to EC2 and run the deployment commands")

if __name__ == "__main__":
    main() 