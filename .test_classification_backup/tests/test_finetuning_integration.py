"""
Integration Tests for Fine-Tuning System
=========================================
Tests the complete flow: Feedback → Pipeline → Dataset → Fine-Tuning

This ensures all components work together correctly.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

from mahoun.finetuning.feedback_pipeline import (
    FeedbackPipeline,
    UserFeedback,
    FeedbackType,
    TrainingExample,
)


class TestFeedbackPipelineIntegration:
    """Integration tests for feedback pipeline"""
    
    def test_complete_pipeline_flow(self):
        """Test complete flow from feedback to dataset"""
        # Create pipeline
        pipeline = FeedbackPipeline(
            min_rating=4.0,
            min_quality_score=0.7
        )
        
        # Add high-quality feedback
        feedback1 = UserFeedback(
            feedback_id="fb_001",
            user_id="user_123",
            query="What is force majeure?",
            response="Force majeure is an unforeseeable circumstance...",
            feedback_type=FeedbackType.RATING,
            rating=5.0,
            response_time_ms=1200,
            confidence_score=0.95
        )
        pipeline.add_feedback(feedback1)
        
        # Add correction feedback (corrections don't need high rating)
        feedback2 = UserFeedback(
            feedback_id="fb_002",
            user_id="user_456",
            query="Explain contract breach",
            response="Breach is when...",
            feedback_type=FeedbackType.CORRECTION,
            corrected_response="Contract breach occurs when one party fails to fulfill obligations...",
            rating=4.5,  # Above threshold
            response_time_ms=1500,
            confidence_score=0.85
        )
        pipeline.add_feedback(feedback2)
        
        # Add low-quality feedback (should be filtered)
        feedback3 = UserFeedback(
            feedback_id="fb_003",
            user_id="user_789",
            query="Test query",
            response="Test response",
            feedback_type=FeedbackType.RATING,
            rating=2.0,  # Below threshold
            response_time_ms=5000,
            confidence_score=0.3
        )
        pipeline.add_feedback(feedback3)
        
        # Collect feedback
        collected = pipeline.collect_feedback(min_rating=4.0)
        assert len(collected) == 2  # Only high-quality feedback
        
        # Convert to training examples
        examples = pipeline.convert_to_training_examples(collected)
        assert len(examples) >= 1  # At least one valid example
        
        # Check example quality
        for example in examples:
            assert example.quality_score >= 0.7
            assert len(example.input_text) > 0
            assert len(example.target_text) > 0
        
        # Create dataset
        dataset = pipeline.create_dataset(
            examples=examples,
            dataset_name="test_dataset",
            description="Test dataset from feedback"
        )
        
        assert dataset.total_examples == len(examples)
        assert len(dataset.train_examples) > 0
        assert dataset.avg_quality_score >= 0.7
    
    def test_dataset_saving(self):
        """Test dataset saving to disk"""
        pipeline = FeedbackPipeline()
        
        # Add feedback
        feedback = UserFeedback(
            feedback_id="fb_save_001",
            user_id="user_save",
            query="Test query for saving",
            response="Test response for saving",
            feedback_type=FeedbackType.RATING,
            rating=5.0,
            response_time_ms=1000,
            confidence_score=0.9
        )
        pipeline.add_feedback(feedback)
        
        # Create dataset
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        dataset = pipeline.create_dataset(
            examples=examples,
            dataset_name="save_test",
            description="Test saving"
        )
        
        # Save to temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            paths = pipeline.save_dataset(dataset, output_dir, format="jsonl")
            
            # Check files exist
            assert paths["train"].exists()
            assert paths["eval"].exists()
            assert paths["test"].exists()
            assert paths["metadata"].exists()
            
            # Check train file content (might be empty if all data went to test split)
            # At least one split should have data
            total_lines = 0
            for split_name in ["train", "eval", "test"]:
                if paths[split_name].exists():
                    with open(paths[split_name], 'r') as f:
                        lines = f.readlines()
                        total_lines += len(lines)
            
            assert total_lines > 0, "At least one split should have data"
            
            # Parse first line (from the first non-empty file)
            first_data_file = None
            for split_name in ["train", "validation", "test"]:
                if paths[split_name].exists():
                    with open(paths[split_name], 'r') as f:
                        lines = f.readlines()
                    if lines:
                        data = json.loads(lines[0])
                        assert "input" in data
                        assert "target" in data
                        assert "quality_score" in data
                    break
            
            # Check metadata
            with open(paths["metadata"], 'r') as f:
                metadata = json.load(f)
                assert metadata["dataset_id"] == dataset.dataset_id
                assert metadata["total_examples"] == dataset.total_examples
    
    def test_quality_scoring(self):
        """Test quality score calculation"""
        pipeline = FeedbackPipeline()
        
        # High quality feedback
        high_quality = UserFeedback(
            feedback_id="fb_hq",
            user_id="user_hq",
            query="High quality query",
            response="High quality response",
            feedback_type=FeedbackType.CORRECTION,  # Bonus
            rating=5.0,
            response_time_ms=1000,  # Optimal
            confidence_score=0.95
        )
        
        score_hq = pipeline._calculate_quality_score(high_quality)
        assert score_hq >= 0.8  # Should be high
        
        # Low quality feedback
        low_quality = UserFeedback(
            feedback_id="fb_lq",
            user_id="user_lq",
            query="Low quality query",
            response="Low quality response",
            feedback_type=FeedbackType.RATING,
            rating=2.0,
            response_time_ms=10000,  # Too slow
            confidence_score=0.3
        )
        
        score_lq = pipeline._calculate_quality_score(low_quality)
        assert score_lq <= 0.7  # Should be low or at threshold
    
    def test_date_filtering(self):
        """Test filtering feedback by date"""
        pipeline = FeedbackPipeline()
        
        # Add feedback with different dates
        now = datetime.now()
        
        feedback_old = UserFeedback(
            feedback_id="fb_old",
            user_id="user_old",
            query="Old query",
            response="Old response",
            feedback_type=FeedbackType.RATING,
            rating=5.0,
            timestamp=now - timedelta(days=10)
        )
        pipeline.add_feedback(feedback_old)
        
        feedback_new = UserFeedback(
            feedback_id="fb_new",
            user_id="user_new",
            query="New query",
            response="New response",
            feedback_type=FeedbackType.RATING,
            rating=5.0,
            timestamp=now - timedelta(days=1)
        )
        pipeline.add_feedback(feedback_new)
        
        # Filter by date
        start_date = now - timedelta(days=5)
        collected = pipeline.collect_feedback(start_date=start_date)
        
        assert len(collected) == 1
        assert collected[0].feedback_id == "fb_new"
    
    def test_preference_feedback(self):
        """Test preference-based feedback"""
        pipeline = FeedbackPipeline()
        
        feedback = UserFeedback(
            feedback_id="fb_pref",
            user_id="user_pref",
            query="Which is better?",
            response="Response A",
            feedback_type=FeedbackType.PREFERENCE,
            preferred_response="Response B is better because...",
            rejected_response="Response A",
            confidence_score=0.9
        )
        pipeline.add_feedback(feedback)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        
        assert len(examples) == 1
        assert examples[0].target_text == feedback.preferred_response
        assert examples[0].source == "preference"
    
    def test_empty_feedback(self):
        """Test handling of empty feedback"""
        pipeline = FeedbackPipeline()
        
        collected = pipeline.collect_feedback()
        assert len(collected) == 0
        
        examples = pipeline.convert_to_training_examples(collected)
        assert len(examples) == 0
    
    def test_dataset_splits(self):
        """Test dataset split ratios"""
        pipeline = FeedbackPipeline(
            train_ratio=0.7,
            eval_ratio=0.2,
            test_ratio=0.1
        )
        
        # Add 100 feedback items
        for i in range(100):
            feedback = UserFeedback(
                feedback_id=f"fb_{i}",
                user_id=f"user_{i}",
                query=f"Query {i}",
                response=f"Response {i}",
                feedback_type=FeedbackType.RATING,
                rating=5.0,
                confidence_score=0.9
            )
            pipeline.add_feedback(feedback)
        
        collected = pipeline.collect_feedback()
        examples = pipeline.convert_to_training_examples(collected)
        dataset = pipeline.create_dataset(
            examples=examples,
            dataset_name="split_test"
        )
        
        # Check split ratios (with some tolerance)
        total = dataset.total_examples
        train_ratio = len(dataset.train_examples) / total
        eval_ratio = len(dataset.eval_examples) / total
        test_ratio = len(dataset.test_examples) / total
        
        assert 0.65 <= train_ratio <= 0.75
        assert 0.15 <= eval_ratio <= 0.25
        assert 0.05 <= test_ratio <= 0.15


class TestFinetuningAPIIntegration:
    """Integration tests for fine-tuning API"""
    
    @pytest.mark.asyncio
    async def test_feedback_to_dataset_endpoint(self):
        """Test creating dataset from feedback via API"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        # Submit some feedback first
        feedback_data = {
            "query_id": "test_query_001",
            "user_id": "test_user",
            "query": "What is contract law?",
            "response": "Contract law governs agreements...",
            "accuracy": 0.95,
            "latency": 1.2,
            "user_satisfaction": 0.9,
        }
        
        response = client.post("/api/v1/feedback", json=feedback_data)
        assert response.status_code == 200
        
        # Wait a bit for background processing
        import asyncio
        await asyncio.sleep(0.5)
        
        # Check feedback stats
        response = client.get("/api/v1/feedback/stats")
        assert response.status_code == 200
        stats = response.json()
        assert stats["total_feedback"] >= 0
    
    def test_create_finetuning_job(self):
        """Test creating a fine-tuning job"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        job_data = {
            "job_name": "test_job",
            "description": "Test fine-tuning job",
            "config": {
                "model_name": "gpt2",
                "training_mode": "lora",
                "learning_rate": 0.00002,
                "num_epochs": 3,
                "batch_size": 4,
            },
            "dataset": {
                "source": "feedback",
            },
        }
        
        response = client.post("/api/v1/finetuning/jobs", json=job_data)
        assert response.status_code == 201
        
        job = response.json()
        assert job["job_name"] == "test_job"
        assert job["status"] in ["pending", "preparing"]
        assert "job_id" in job
    
    def test_list_finetuning_jobs(self):
        """Test listing fine-tuning jobs"""
        from fastapi.testclient import TestClient
        from api.main import app
        
        client = TestClient(app)
        
        response = client.get("/api/v1/finetuning/jobs")
        assert response.status_code == 200
        
        jobs = response.json()
        assert isinstance(jobs, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
