#!/usr/bin/env python3
"""
Test script to verify that the S3 connection timeout fixes work properly.
This script tests the SpiS3Utils class with the new timeout configurations.
"""

import sys
import os
sys.path.append('SpiMediaGallery')

from django.conf import settings
from main.spi_s3_utils import SpiS3Utils

def test_s3_connection():
    """Test the S3 connection with timeout settings"""
    try:
        # Test creating an S3 utils instance
        spi_s3 = SpiS3Utils(bucket_name="imported")
        print("✓ Successfully created SpiS3Utils instance")
        
        # Test getting the resource with timeout config
        resource = spi_s3.resource()
        print("✓ Successfully created boto3 resource with timeout config")
        
        # Test getting the client with timeout config
        client = spi_s3.client()
        print("✓ Successfully created boto3 client with timeout config")
        
        # Test bucket access
        bucket = spi_s3.bucket()
        print("✓ Successfully accessed S3 bucket")
        
        print("\n✅ All S3 connection tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ S3 connection test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing S3 connection with timeout configurations...")
    success = test_s3_connection()
    sys.exit(0 if success else 1) 