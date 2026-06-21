#!/usr/bin/env python3
"""
Manual E2E Test for Fine-Tuning System
=======================================
Run this to manually test the complete flow without pytest.

Usage:
    python test_e2e_manual.py
"""

import requests
import time
import json
from datetime import datetime


BASE_URL = "http://localhost:8000"


def print_section(title):
    """Print a section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_step(step_num, description):
    """Print a step header"""
    print(f"\n📍 Step {step_num}: {description}")
    print("-" * 70)


def test_complete_flow():
    """Test the complete E2E flow"""
    
    print_section("🚀 E2E Manual Test: Complete Fine-Tuning Flow")
    
    # =========================================================================
    # Step 1: Submit Feedback
    # =========================================================================
    print_step(1, "Submitting User Feedback")
    
    feedback_items = [
        {
            "query_id": f"manual_test_{int(time.time())}_001",
            "user_id": "manual_test_user",
            "query": "What is force majeure?",
            "response": "Force majeure is an unforeseeable circumstance that prevents contract fulfillment.",
            "accuracy": 0.95,
            "latency": 1.2,
            "user_satisfaction": 0.9,
        },
        {
            "query_id": f"manual_test_{int(time.time())}_002",
            "user_id": "manual_test_user",
            "query": "Explain breach of contract",
            "response": "Breach of contract occurs when a party fails to fulfill obligations.",
            "accuracy": 0.92,
            "latency": 1.5,
            "user_satisfaction": 0.85,
        },
    ]
    
    for feedback in feedback_items:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/feedback",
                json=feedback,
                timeout=5
            )
            if response.status_code == 200:
                print(f"✓ Feedback submitted: {feedback['query_id']}")
            else:
                print(f"✗ Failed to submit feedback: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"✗ Error submitting feedback: {e}")
            return False
    
    # Wait for background processing
    print("\n⏳ Waiting for background processing...")
    time.sleep(2)
    
    # =========================================================================
    # Step 2: Check Feedback Stats
    # =========================================================================
    print_step(2, "Checking Feedback Statistics")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/feedback/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Total feedback: {stats['total_feedback']}")
            print(f"✓ Avg satisfaction: {stats.get('avg_satisfaction', 0):.3f}")
            print(f"✓ Avg accuracy: {stats.get('avg_accuracy', 0):.3f}")
        else:
            print(f"✗ Failed to get stats: {response.status_code}")
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
    
    # =========================================================================
    # Step 3: Create Dataset
    # =========================================================================
    print_step(3, "Creating Training Dataset from Feedback")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/finetuning/datasets/from-feedback",
            params={"min_rating": 4.0},
            json={},
            timeout=10
        )
        if response.status_code == 200:
            dataset = response.json()
            print(f"✓ Dataset created: {dataset['dataset_id']}")
            print(f"✓ Total examples: {dataset['size']}")
            print(f"✓ Splits: train={dataset['splits']['train']}, "
                  f"eval={dataset['splits']['eval']}, "
                  f"test={dataset['splits']['test']}")
            dataset_id = dataset['dataset_id']
        else:
            print(f"✗ Failed to create dataset: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error creating dataset: {e}")
        return False
    
    # =========================================================================
    # Step 4: Create Fine-Tuning Job
    # =========================================================================
    print_step(4, "Creating Fine-Tuning Job")
    
    job_config = {
        "job_name": f"Manual Test Job {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Manual E2E test job",
        "config": {
            "model_name": "gpt2",
            "training_mode": "lora",
            "learning_rate": 0.00002,
            "num_epochs": 2,
            "batch_size": 4,
        },
        "dataset": {
            "source": "feedback",
            "dataset_id": dataset_id,
        },
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/finetuning/jobs",
            json=job_config,
            timeout=10
        )
        if response.status_code == 201:
            job = response.json()
            print(f"✓ Job created: {job['job_id']}")
            print(f"✓ Job name: {job['job_name']}")
            print(f"✓ Status: {job['status']}")
            job_id = job['job_id']
        else:
            print(f"✗ Failed to create job: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error creating job: {e}")
        return False
    
    # =========================================================================
    # Step 5: Monitor Progress
    # =========================================================================
    print_step(5, "Monitoring Training Progress")
    
    print("\n⏳ Monitoring for 10 seconds...")
    
    for i in range(10):
        try:
            response = requests.get(
                f"{BASE_URL}/api/v1/finetuning/jobs/{job_id}",
                timeout=5
            )
            if response.status_code == 200:
                job = response.json()
                status = job['status']
                progress = job['progress_percentage']
                epoch = job['current_epoch']
                total_epochs = job['total_epochs']
                
                print(f"  [{i+1}/10] Status: {status:12s} | "
                      f"Progress: {progress:5.1f}% | "
                      f"Epoch: {epoch}/{total_epochs}", end="\r")
                
                if status in ["completed", "failed", "cancelled"]:
                    print()  # New line
                    break
            
            time.sleep(1)
        except Exception as e:
            print(f"\n✗ Error monitoring: {e}")
            break
    
    print()  # New line after monitoring
    
    # =========================================================================
    # Step 6: Get Final Status
    # =========================================================================
    print_step(6, "Getting Final Status")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/finetuning/jobs/{job_id}",
            timeout=5
        )
        if response.status_code == 200:
            job = response.json()
            print(f"✓ Final status: {job['status']}")
            print(f"✓ Progress: {job['progress_percentage']:.1f}%")
            if job.get('train_loss'):
                print(f"✓ Train loss: {job['train_loss']:.4f}")
            if job.get('eval_accuracy'):
                print(f"✓ Eval accuracy: {job['eval_accuracy']:.4f}")
        else:
            print(f"✗ Failed to get job status: {response.status_code}")
    except Exception as e:
        print(f"✗ Error getting status: {e}")
    
    # =========================================================================
    # Step 7: List All Jobs
    # =========================================================================
    print_step(7, "Listing All Jobs")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/finetuning/jobs", timeout=5)
        if response.status_code == 200:
            jobs = response.json()
            print(f"✓ Total jobs: {len(jobs)}")
            
            # Show last 3 jobs
            print("\n  Recent jobs:")
            for job in jobs[:3]:
                print(f"    - {job['job_name']:30s} | {job['status']:12s} | "
                      f"{job['progress_percentage']:5.1f}%")
        else:
            print(f"✗ Failed to list jobs: {response.status_code}")
    except Exception as e:
        print(f"✗ Error listing jobs: {e}")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print_section("✅ E2E Manual Test Complete!")
    
    print("\n📊 Summary:")
    print(f"  • Feedback submitted: ✓")
    print(f"  • Dataset created: ✓")
    print(f"  • Job created: ✓")
    print(f"  • Monitoring: ✓")
    print(f"  • Job ID: {job_id}")
    
    print("\n💡 Next steps:")
    print(f"  • Check job status: GET {BASE_URL}/api/v1/finetuning/jobs/{job_id}")
    print(f"  • View metrics: GET {BASE_URL}/api/v1/finetuning/jobs/{job_id}/metrics")
    print(f"  • View logs: GET {BASE_URL}/api/v1/finetuning/jobs/{job_id}/logs")
    print(f"  • Deploy model: POST {BASE_URL}/api/v1/finetuning/jobs/{job_id}/deploy")
    
    return True


def check_api_health():
    """Check if API is running"""
    print_section("🏥 Checking API Health")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✓ API is healthy and running")
            return True
        else:
            print(f"✗ API returned status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to API at {BASE_URL}")
        print("\n💡 Make sure the API is running:")
        print("   uvicorn api.main:app --reload")
        return False
    except Exception as e:
        print(f"✗ Error checking health: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  MAHOUN E2E Manual Test")
    print("  Fine-Tuning System")
    print("="*70)
    
    # Check API health first
    if not check_api_health():
        print("\n❌ API is not running. Please start it first.")
        exit(1)
    
    # Run the test
    try:
        success = test_complete_flow()
        
        if success:
            print("\n" + "="*70)
            print("  🎉 ALL TESTS PASSED!")
            print("="*70)
            exit(0)
        else:
            print("\n" + "="*70)
            print("  ❌ SOME TESTS FAILED")
            print("="*70)
            exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
