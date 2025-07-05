#!/usr/bin/env python3
"""
AWS Deployment Script for Capture Moments
This script helps set up DynamoDB tables and prepare for deployment
"""

import boto3
import json
from botocore.exceptions import ClientError

def create_dynamodb_tables(region_name='ap-south-1'):
    """Create DynamoDB tables for the application"""
    
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    
    # Table definitions
    tables = {
        'users': {
            'KeySchema': [
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        'photographers': {
            'KeySchema': [
                {'AttributeName': 'photographer_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'photographer_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        },
        'booking': {
            'KeySchema': [
                {'AttributeName': 'booking_id', 'KeyType': 'HASH'}
            ],
            'AttributeDefinitions': [
                {'AttributeName': 'booking_id', 'AttributeType': 'S'}
            ],
            'BillingMode': 'PAY_PER_REQUEST'
        }
    }
    
    created_tables = []
    
    for table_name, table_config in tables.items():
        try:
            # Check if table exists
            table = dynamodb.Table(table_name)
            table.load()
            print(f"✅ Table '{table_name}' already exists")
            created_tables.append(table_name)
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
            else:
                print(f"❌ Error checking table '{table_name}': {e}")
    
    return created_tables

def add_sample_photographers(region_name='ap-south-1'):
    """Add sample photographers to DynamoDB"""
    
    dynamodb = boto3.resource('dynamodb', region_name=region_name)
    table = dynamodb.Table('photographers')
    
    sample_photographers = [
        {
            'photographer_id': 'photo_001',
            'Name': 'John Smith',
            'Skills': 'Portrait, Wedding, Event',
            'Location': 'Mumbai',
            'price_per_hour': 1500.0,
            'Photo': 'https://example.com/john.jpg',
            'availability': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        },
        {
            'photographer_id': 'photo_002',
            'Name': 'Sarah Johnson',
            'Skills': 'Fashion, Commercial, Product',
            'Location': 'Delhi',
            'price_per_hour': 2000.0,
            'Photo': 'https://example.com/sarah.jpg',
            'availability': ['Monday', 'Tuesday', 'Wednesday', 'Saturday', 'Sunday']
        },
        {
            'photographer_id': 'photo_003',
            'Name': 'Mike Wilson',
            'Skills': 'Landscape, Nature, Wildlife',
            'Location': 'Bangalore',
            'price_per_hour': 1200.0,
            'Photo': 'https://example.com/mike.jpg',
            'availability': ['Friday', 'Saturday', 'Sunday']
        }
    ]
    
    for photographer in sample_photographers:
        try:
            table.put_item(Item=photographer)
            print(f"✅ Added photographer: {photographer['Name']}")
        except Exception as e:
            print(f"❌ Failed to add photographer {photographer['Name']}: {e}")

def main():
    """Main deployment function"""
    
    print("🚀 AWS Deployment Setup for Capture Moments")
    print("=" * 50)
    
    # Get region
    region = input("Enter AWS region (default: ap-south-1): ").strip() or 'ap-south-1'
    
    try:
        # Create tables
        print("\n📊 Creating DynamoDB tables...")
        created_tables = create_dynamodb_tables(region)
        
        if created_tables:
            print(f"\n✅ Successfully created/verified {len(created_tables)} tables:")
            for table in created_tables:
                print(f"   - {table}")
        
        # Add sample data
        add_sample = input("\n📸 Add sample photographers? (y/n): ").strip().lower()
        if add_sample == 'y':
            print("\n📸 Adding sample photographers...")
            add_sample_photographers(region)
        
        print("\n🎉 Setup complete!")
        print("\nNext steps:")
        print("1. Install AWS CLI: pip install awscli")
        print("2. Configure AWS: aws configure")
        print("3. Install EB CLI: pip install awsebcli")
        print("4. Initialize EB: eb init capture-moments --platform python-3.11 --region " + region)
        print("5. Create environment: eb create capture-moments-env")
        print("6. Deploy: eb deploy")
        
    except Exception as e:
        print(f"\n❌ Deployment setup failed: {e}")
        print("Please check your AWS credentials and permissions.")

if __name__ == "__main__":
    main() 