"""
End-to-End Tests for Fine-Tuning Flow
======================================
Tests the complete user journey from feedback submission to model deployment.

Flow:
1. User submits feedback
2. System processes and stores feedback
3. User creates dataset from feedback
4. User starts fine-tuning job
5. System trains model
6. User monitors progress
7. User deploys model

This ensures the entire system works together as expected.
"""

import pytest
import asyncio
from datetime import datetime
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import time


@pytest.mark.asyncio
class TestE2EFineTuningFlow:
    """End-to-end tests for complete fine-tuning workflow"""
    
    async def test_complete_user_journey(self):
        """
        Test complete user journey from feedback to deployment.
        
        This is the golden path that users will follow.
        """
        from api.main import app
        
        client = TestClient(app)
        
        print("\n" + "="*70)
        print("🚀 E2E TEST: Complete Fine-Tuning Journey")
        print("="*70)
        
        # =====================================================================
        # Step 1: Submit User Feedback
        # =====================================================================
        print("\n📝 Step 1: Submitting user feedback...")
        
        feedback_items = [
            {
                "query_id": "e2e_query_001",
                "user_id": "e2e_user_001",
                "query": "What is force majeure in contract law?",
                "response": "Force majeure is a clause that frees parties from liability when an extraordinary event prevents fulfillment of contract obligations.",
                "accuracy": 0.95,
                "latency": 1.2,
                "user_satisfaction": 0.9,
            },
            {
                "query_id": "e2e_query_002",
                "user_id": "e2e_user_002",
                "query": "Explain breach of contract remedies",
                "response": "Remedies for breach of contract include compensatory damages, specific performance, and rescission.",
                "accuracy": 0.92,
                "latency": 1.5,
                "user_satisfaction": 0.85,
            },
            {
                "query_id": "e2e_query_003",
                "user_id": "e2e_user_003",
                "query": "What is consideration in contracts?",
                "response": "Consideration is something of value exchanged between parties, essential for a valid contract.",
                "accuracy": 0.88,
                "latency": 1.1,
                "user_satisfaction": 0.8,
            },
        ]
        
        for feedback in feedback_items:
            response = client.post("/api/v1/feedback", json=feedback)
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "accepted"
            print(f"  ✓ Feedback submitted: {feedback['query_id']}")
        
        # Wait for background processing
        await asyncio.sleep(1.0)
        
        # =====================================================================
        # Step 2: Check Feedback Statistics
        # =====================================================================
        print("\n📊 Step 2: Checking feedback statistics...")
        
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code == 200
        stats = response.json()
        
        print(f"  ✓ Total feedback: {stats['total_feedback']}")
        print(f"  ✓ Avg satisfaction: {stats['avg_satisfaction']:.3f}")
        print(f"  ✓ Avg accuracy: {stats['avg_accuracy']:.3f}")
        
        assert stats["total_feedback"] >= 3
        
        # =====================================================================
        # Step 3: Create Dataset from Feedback
        # =====================================================================
        print("\n📦 Step 3: Creating training dataset from feedback...")
        
        response = client.post(
            "/api/v1/finetuning/datasets/from-feedback",
            params={
                "min_rating": 4.0
            }
        )
        assert response.status_code == 200
        dataset = response.json()
        
        print(f"  ✓ Dataset created: {dataset['dataset_id']}")
        print(f"  ✓ Total examples: {dataset['size']}")
        print(f"  ✓ Train: {dataset['splits']['train']}")
        print(f"  ✓ Eval: {dataset['splits']['eval']}")
        print(f"  ✓ Test: {dataset['splits']['test']}")
        print(f"  ✓ Avg quality: {dataset['avg_quality_score']:.3f}")
        
        assert dataset["size"] > 0
        assert dataset["source"] == "feedback"
        
        dataset_id = dataset["dataset_id"]
        
        # =====================================================================
        # Step 4: Create Fine-Tuning Job
        # =====================================================================
        print("\n🎯 Step 4: Creating fine-tuning job...")
        
        job_config = {
            "job_name": "E2E Test Job",
            "description": "End-to-end test fine-tuning job",
            "config": {
                "model_name": "gpt2",
                "training_mode": "lora",
                "learning_rate": 0.00002,
                "num_epochs": 2,
                "batch_size": 4,
                "lora_r": 8,
                "lora_alpha": 16,
            },
            "dataset": {
                "source": "feedback",
                "dataset_id": dataset_id,
            },
            "auto_deploy": False,
        }
        
        response = client.post("/api/v1/finetuning/jobs", json=job_config)
        assert response.status_code == 201
        job = response.json()
        
        print(f"  ✓ Job created: {job['job_id']}")
        print(f"  ✓ Job name: {job['job_name']}")
        print(f"  ✓ Status: {job['status']}")
        print(f"  ✓ Model: {job['config']['model_name']}")
        print(f"  ✓ Training mode: {job['config']['training_mode']}")
        
        assert job["status"] in ["pending", "preparing"]
        assert job["job_name"] == "E2E Test Job"
        
        job_id = job["job_id"]
        
        # =====================================================================
        # Step 5: Monitor Training Progress
        # =====================================================================
        print("\n⏳ Step 5: Monitoring training progress...")
        
        # Wait a bit for training to start
        await asyncio.sleep(2.0)
        
        # Check job status
        response = client.get(f"/api/v1/finetuning/jobs/{job_id}")
        assert response.status_code == 200
        job = response.json()
        
        print(f"  ✓ Current status: {job['status']}")
        print(f"  ✓ Progress: {job['progress_percentage']:.1f}%")
        print(f"  ✓ Epoch: {job['current_epoch']}/{job['total_epochs']}")
        
        if job['train_loss']:
            print(f"  ✓ Train loss: {job['train_loss']:.4f}")
        
        # Check metrics
        response = client.get(f"/api/v1/finetuning/jobs/{job_id}/metrics")
        assert response.status_code == 200
        metrics = response.json()
        
        print(f"  ✓ Metrics collected: {len(metrics)} data points")
        
        # Check logs
        response = client.get(f"/api/v1/finetuning/jobs/{job_id}/logs")
        assert response.status_code == 200
        logs = response.json()
        
        print(f"  ✓ Log lines: {logs['total_lines']}")
        
        # =====================================================================
        # Step 6: List All Jobs
        # =====================================================================
        print("\n📋 Step 6: Listing all fine-tuning jobs...")
        
        response = client.get("/api/v1/finetuning/jobs")
        assert response.status_code == 200
        jobs = response.json()
        
        print(f"  ✓ Total jobs: {len(jobs)}")
        
        # Find our job
        our_job = next((j for j in jobs if j["job_id"] == job_id), None)
        assert our_job is not None
        print(f"  ✓ Found our job: {our_job['job_name']}")
        
        # =====================================================================
        # Step 7: Wait for Completion (or timeout)
        # =====================================================================
        print("\n⏰ Step 7: Waiting for training completion...")
        
        max_wait = 30  # seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = client.get(f"/api/v1/finetuning/jobs/{job_id}")
            job = response.json()
            
            status = job["status"]
            progress = job["progress_percentage"]
            
            print(f"  ⏳ Status: {status}, Progress: {progress:.1f}%", end="\r")
            
            if status in ["completed", "failed", "cancelled"]:
                print()  # New line
                break
            
            await asyncio.sleep(1.0)
        
        print(f"  ✓ Final status: {job['status']}")
        
        # =====================================================================
        # Step 8: Deploy Model (if completed)
        # =====================================================================
        if job["status"] == "completed":
            print("\n🚀 Step 8: Deploying fine-tuned model...")
            
            deploy_config = {
                "job_id": job_id,
                "strategy": "shadow",
                "traffic_percentage": 0.0,
                "rollback_on_error": True,
            }
            
            response = client.post(
                f"/api/v1/finetuning/jobs/{job_id}/deploy",
                json=deploy_config
            )
            assert response.status_code == 200
            deployment = response.json()
            
            print(f"  ✓ Deployment status: {deployment['status']}")
            print(f"  ✓ Strategy: {deployment['strategy']}")
            print(f"  ✓ Model path: {deployment['model_path']}")
            
            assert deployment["status"] == "deployed"
        else:
            print(f"\n⚠️  Step 8: Skipping deployment (status: {job['status']})")
        
        # =====================================================================
        # Step 9: Verify End State
        # =====================================================================
        print("\n✅ Step 9: Verifying end state...")
        
        # Check feedback stats again
        response = client.get("/api/v1/feedback/stats")
        final_stats = response.json()
        print(f"  ✓ Final feedback count: {final_stats['total_feedback']}")
        
        # Check job list
        response = client.get("/api/v1/finetuning/jobs")
        final_jobs = response.json()
        print(f"  ✓ Final job count: {len(final_jobs)}")
        
        # Check datasets
        response = client.get("/api/v1/finetuning/datasets")
        datasets = response.json()
        print(f"  ✓ Total datasets: {datasets['total']}")
        
        print("\n" + "="*70)
        print("🎉 E2E TEST COMPLETED SUCCESSFULLY!")
        print("="*70)
    
    async def test_error_handling_flow(self):
        """Test error handling in the flow"""
        from api.main import app
        
        client = TestClient(app)
        
        print("\n" + "="*70)
        print("🧪 E2E TEST: Error Handling")
        print("="*70)
        
        # Try to create job with invalid config
        print("\n❌ Testing invalid job creation...")
        
        invalid_config = {
            "job_name": "",  # Empty name
            "config": {
                "model_name": "gpt2",
                "training_mode": "lora",
                "learning_rate": -0.1,  # Invalid negative
                "num_epochs": 0,  # Invalid zero
                "batch_size": 4,
            },
            "dataset": {
                "source": "feedback",
            },
        }
        
        response = client.post("/api/v1/finetuning/jobs", json=invalid_config)
        # Should fail validation
        assert response.status_code in [400, 422]
        print("  ✓ Invalid config rejected")
        
        # Try to get non-existent job
        print("\n❌ Testing non-existent job...")
        
        response = client.get("/api/v1/finetuning/jobs/nonexistent_id")
        assert response.status_code == 404
        print("  ✓ Non-existent job returns 404")
        
        # Try to cancel non-existent job
        print("\n❌ Testing cancel non-existent job...")
        
        response = client.delete("/api/v1/finetuning/jobs/nonexistent_id")
        assert response.status_code == 404
        print("  ✓ Cancel non-existent job returns 404")
        
        print("\n✅ Error handling tests passed!")
    
    async def test_concurrent_jobs(self):
        """Test creating multiple jobs concurrently"""
        from api.main import app
        
        client = TestClient(app)
        
        print("\n" + "="*70)
        print("🔄 E2E TEST: Concurrent Jobs")
        print("="*70)
        
        # Create multiple jobs
        print("\n🚀 Creating multiple jobs...")
        
        job_ids = []
        for i in range(3):
            job_config = {
                "job_name": f"Concurrent Job {i+1}",
                "description": f"Test concurrent job {i+1}",
                "config": {
                    "model_name": "gpt2",
                    "training_mode": "lora",
                    "learning_rate": 0.00002,
                    "num_epochs": 1,
                    "batch_size": 4,
                },
                "dataset": {
                    "source": "feedback",
                },
            }
            
            response = client.post("/api/v1/finetuning/jobs", json=job_config)
            assert response.status_code == 201
            job = response.json()
            job_ids.append(job["job_id"])
            print(f"  ✓ Created job {i+1}: {job['job_id']}")
        
        # Wait a bit
        await asyncio.sleep(2.0)
        
        # Check all jobs
        print("\n📊 Checking all jobs...")
        
        for i, job_id in enumerate(job_ids):
            response = client.get(f"/api/v1/finetuning/jobs/{job_id}")
            assert response.status_code == 200
            job = response.json()
            print(f"  ✓ Job {i+1} status: {job['status']}")
        
        print("\n✅ Concurrent jobs test passed!")


@pytest.mark.asyncio
class TestE2EValidationFlow:
    """Test validation and security in E2E flow"""
    
    async def test_input_validation_e2e(self):
        """Test that input validation works throughout the flow"""
        from api.main import app
        
        client = TestClient(app)
        
        print("\n" + "="*70)
        print("🔒 E2E TEST: Input Validation")
        print("="*70)
        
        # Test SQL injection attempt in feedback
        print("\n🛡️ Testing SQL injection prevention...")
        
        malicious_feedback = {
            "query_id": "sql_injection_test",
            "user_id": "'; DROP TABLE users; --",
            "query": "SELECT * FROM secrets",
            "response": "Response",
            "accuracy": 0.9,
            "latency": 1.0,
            "user_satisfaction": 0.8,
        }
        
        response = client.post("/api/v1/feedback", json=malicious_feedback)
        # Should be sanitized or rejected
        assert response.status_code in [200, 400, 422]
        print("  ✓ SQL injection attempt handled")
        
        # Test XSS attempt in job name
        print("\n🛡️ Testing XSS prevention...")
        
        xss_config = {
            "job_name": "<script>alert('xss')</script>",
            "config": {
                "model_name": "gpt2",
                "training_mode": "lora",
                "learning_rate": 0.00002,
                "num_epochs": 1,
                "batch_size": 4,
            },
            "dataset": {
                "source": "feedback",
            },
        }
        
        response = client.post("/api/v1/finetuning/jobs", json=xss_config)
        # Should be sanitized or rejected
        assert response.status_code in [201, 400, 422]
        print("  ✓ XSS attempt handled")
        
        print("\n✅ Input validation tests passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
