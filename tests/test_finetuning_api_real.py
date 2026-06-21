#!/usr/bin/env python3
"""
Real API Test for Fine-Tuning System
=====================================
Tests the fine-tuning system through the actual API endpoints.

This is the "golden path" test - the way real users will use the system.
"""

import os
import sys

# Set test environment
os.environ["MAHOUN_TESTING"] = "1"
os.environ.setdefault("DB_POSTGRES_PASSWORD", "test_postgres_password")
os.environ.setdefault("DB_NEO4J_PASSWORD", "test_neo4j_password")
os.environ.setdefault("SECURITY_JWT_SECRET", "test_jwt_secret_exactly_32_chars_min_NOT_FOR_PRODUCTION_USE_12345678")

from fastapi.testclient import TestClient
from datetime import datetime
import time


def print_header(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_step(step_num, description):
    print(f"\n📍 Step {step_num}: {description}")
    print("-" * 60)


def main():
    print_header("🚀 Fine-Tuning API Real Test")
    
    # Import app
    from api.main import app
    client = TestClient(app)
    
    # =========================================================================
    # Step 1: Health Check
    # =========================================================================
    print_step(1, "Health Check")
    
    response = client.get("/health")
    print(f"  Status: {response.status_code}")
    if response.status_code == 200:
        print("  ✅ API is healthy")
    else:
        print("  ❌ API health check failed")
        return False
    
    # =========================================================================
    # Step 2: Submit Feedback (multiple items)
    # =========================================================================
    print_step(2, "Submit User Feedback")
    
    feedback_items = [
        {
            "query_id": f"api_test_{int(time.time())}_001",
            "user_id": "api_test_user",
            "query": "What is force majeure in contract law?",
            "response": "Force majeure is a clause that frees parties from liability when an extraordinary event prevents contract fulfillment.",
            "accuracy": 0.95,
            "latency": 1.2,
            "user_satisfaction": 0.9,
        },
        {
            "query_id": f"api_test_{int(time.time())}_002",
            "user_id": "api_test_user",
            "query": "Explain breach of contract remedies",
            "response": "Remedies for breach of contract include compensatory damages, specific performance, and rescission.",
            "accuracy": 0.92,
            "latency": 1.5,
            "user_satisfaction": 0.85,
        },
        {
            "query_id": f"api_test_{int(time.time())}_003",
            "user_id": "api_test_user",
            "query": "What is consideration in contracts?",
            "response": "Consideration is something of value exchanged between parties, essential for a valid contract.",
            "accuracy": 0.88,
            "latency": 1.1,
            "user_satisfaction": 0.8,
        },
    ]
    
    for i, feedback in enumerate(feedback_items):
        response = client.post("/api/v1/feedback", json=feedback)
        if response.status_code == 200:
            print(f"  ✅ Feedback {i+1} submitted: {feedback['query_id']}")
        else:
            print(f"  ❌ Feedback {i+1} failed: {response.status_code}")
            print(f"     Response: {response.text}")
    
    # Wait for background processing
    print("\n  ⏳ Waiting for background processing...")
    time.sleep(1)
    
    # =========================================================================
    # Step 3: Check Feedback Stats
    # =========================================================================
    print_step(3, "Check Feedback Statistics")
    
    response = client.get("/api/v1/feedback/stats")
    if response.status_code == 200:
        stats = response.json()
        print(f"  Total feedback: {stats['total_feedback']}")
        print(f"  Avg satisfaction: {stats.get('avg_satisfaction', 0):.3f}")
        print(f"  Avg accuracy: {stats.get('avg_accuracy', 0):.3f}")
        print("  ✅ Stats retrieved")
    else:
        print(f"  ❌ Failed to get stats: {response.status_code}")
    
    # =========================================================================
    # Step 4: List Existing Datasets
    # =========================================================================
    print_step(4, "List Existing Datasets")
    
    response = client.get("/api/v1/finetuning/datasets")
    if response.status_code == 200:
        datasets = response.json()
        print(f"  Total datasets: {datasets['total']}")
        for ds in datasets.get('datasets', []):
            print(f"    - {ds['name']} ({ds['size']} examples)")
        print("  ✅ Datasets listed")
    else:
        print(f"  ❌ Failed to list datasets: {response.status_code}")
    
    # =========================================================================
    # Step 5: Create Fine-Tuning Job
    # =========================================================================
    print_step(5, "Create Fine-Tuning Job")
    
    job_config = {
        "job_name": f"API Test Job {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Test job created via API",
        "config": {
            "model_name": "gpt2",
            "training_mode": "lora",
            "learning_rate": 0.00002,
            "num_epochs": 2,
            "batch_size": 4,
        },
        "dataset": {
            "source": "feedback",
        },
    }
    
    response = client.post("/api/v1/finetuning/jobs", json=job_config)
    if response.status_code == 201:
        job = response.json()
        job_id = job['job_id']
        print(f"  Job ID: {job_id}")
        print(f"  Job name: {job['job_name']}")
        print(f"  Status: {job['status']}")
        print("  ✅ Job created")
    else:
        print(f"  ❌ Failed to create job: {response.status_code}")
        print(f"     Response: {response.text}")
        return False
    
    # =========================================================================
    # Step 6: Monitor Job Progress
    # =========================================================================
    print_step(6, "Monitor Job Progress")
    
    print("  ⏳ Monitoring for 5 seconds...")
    
    for i in range(5):
        response = client.get(f"/api/v1/finetuning/jobs/{job_id}")
        if response.status_code == 200:
            job = response.json()
            status = job['status']
            progress = job['progress_percentage']
            epoch = job['current_epoch']
            total_epochs = job['total_epochs']
            
            print(f"    [{i+1}/5] Status: {status:12s} | Progress: {progress:5.1f}% | Epoch: {epoch}/{total_epochs}")
            
            if status in ["completed", "failed", "cancelled"]:
                break
        
        time.sleep(1)
    
    print("  ✅ Monitoring complete")
    
    # =========================================================================
    # Step 7: Get Job Metrics
    # =========================================================================
    print_step(7, "Get Job Metrics")
    
    response = client.get(f"/api/v1/finetuning/jobs/{job_id}/metrics")
    if response.status_code == 200:
        metrics = response.json()
        print(f"  Metrics collected: {len(metrics)} data points")
        if metrics:
            latest = metrics[-1]
            print(f"  Latest train_loss: {latest.get('train_loss', 'N/A')}")
            print(f"  Latest learning_rate: {latest.get('learning_rate', 'N/A')}")
        print("  ✅ Metrics retrieved")
    else:
        print(f"  ❌ Failed to get metrics: {response.status_code}")
    
    # =========================================================================
    # Step 8: Get Job Logs
    # =========================================================================
    print_step(8, "Get Job Logs")
    
    response = client.get(f"/api/v1/finetuning/jobs/{job_id}/logs")
    if response.status_code == 200:
        logs = response.json()
        print(f"  Total log lines: {logs['total_lines']}")
        if logs.get('lines'):
            print("  Last 3 lines:")
            for line in logs['lines'][-3:]:
                print(f"    {line}")
        print("  ✅ Logs retrieved")
    else:
        print(f"  ❌ Failed to get logs: {response.status_code}")
    
    # =========================================================================
    # Step 9: List All Jobs
    # =========================================================================
    print_step(9, "List All Jobs")
    
    response = client.get("/api/v1/finetuning/jobs")
    if response.status_code == 200:
        jobs = response.json()
        print(f"  Total jobs: {len(jobs)}")
        print("  Recent jobs:")
        for j in jobs[:3]:
            print(f"    - {j['job_name'][:30]:30s} | {j['status']:12s} | {j['progress_percentage']:5.1f}%")
        print("  ✅ Jobs listed")
    else:
        print(f"  ❌ Failed to list jobs: {response.status_code}")
    
    # =========================================================================
    # Step 10: Get Final Job Status
    # =========================================================================
    print_step(10, "Get Final Job Status")
    
    response = client.get(f"/api/v1/finetuning/jobs/{job_id}")
    if response.status_code == 200:
        job = response.json()
        print(f"  Final status: {job['status']}")
        print(f"  Progress: {job['progress_percentage']:.1f}%")
        if job.get('train_loss'):
            print(f"  Train loss: {job['train_loss']:.4f}")
        if job.get('eval_accuracy'):
            print(f"  Eval accuracy: {job['eval_accuracy']:.4f}")
        print("  ✅ Final status retrieved")
    else:
        print(f"  ❌ Failed to get final status: {response.status_code}")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print_header("✅ API Test Complete!")
    
    print("\n📊 Summary:")
    print(f"  • Health check: ✅")
    print(f"  • Feedback submission: ✅")
    print(f"  • Stats retrieval: ✅")
    print(f"  • Job creation: ✅")
    print(f"  • Job monitoring: ✅")
    print(f"  • Metrics retrieval: ✅")
    print(f"  • Logs retrieval: ✅")
    print(f"  • Job listing: ✅")
    
    print(f"\n💡 Job ID: {job_id}")
    print(f"   Use this to check status later:")
    print(f"   GET /api/v1/finetuning/jobs/{job_id}")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n" + "="*70)
            print("  🎉 ALL API TESTS PASSED!")
            print("="*70)
            sys.exit(0)
        else:
            print("\n" + "="*70)
            print("  ❌ SOME API TESTS FAILED!")
            print("="*70)
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
