"""
Tests for LocalLLMDriver
=========================
Comprehensive tests for production-grade local LLM driver.

Test Coverage:
- Initialization
- Model loading (with mocking)
- Text generation
- Batch generation
- Error handling
- Metrics tracking
- Memory management
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import torch

from mahoun.llm.local_driver import (
    LocalLLMDriver,
    GenerationConfig,
    ModelMetrics
)


class TestLocalLLMDriver:
    """Test suite for LocalLLMDriver"""
    
    def test_initialization(self, tmp_path):
        """Test driver initialization"""
        driver = LocalLLMDriver(
            model_dir=str(tmp_path),
            use_quantization=True,
            device="cpu"
        )
        
        assert driver.model_dir == tmp_path
        assert driver.use_quantization is True
        assert driver.device == "cpu"
        assert driver.model is None
        assert driver.tokenizer is None
        assert isinstance(driver.metrics, ModelMetrics)
    
    def test_initialization_creates_model_dir(self, tmp_path):
        """Test that model directory is created if it doesn't exist"""
        model_dir = tmp_path / "nonexistent"
        driver = LocalLLMDriver(model_dir=str(model_dir))
        
        assert model_dir.exists()
    
    def test_load_model_not_found(self, tmp_path):
        """Test loading non-existent model raises error"""
        driver = LocalLLMDriver(model_dir=str(tmp_path))
        
        with pytest.raises(FileNotFoundError) as exc_info:
            driver.load("nonexistent-model")
        
        assert "not found" in str(exc_info.value).lower()
    
    @patch('mahoun.llm.local_driver.AutoTokenizer')
    @patch('mahoun.llm.local_driver.AutoModelForCausalLM')
    def test_load_model_success(self, mock_model_class, mock_tokenizer_class, tmp_path):
        """Test successful model loading"""
        # Create fake model directory
        model_dir = tmp_path / "test-model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}")
        
        # Mock tokenizer and model
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "<eos>"
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model
        
        # Load model
        driver = LocalLLMDriver(
            model_dir=str(tmp_path),
            use_quantization=False,
            device="cpu"
        )
        driver.load("test-model")
        
        # Verify
        assert driver.model is not None
        assert driver.tokenizer is not None
        assert driver.model_name == "test-model"
        assert driver.metrics.load_time_seconds > 0
    
    @patch('mahoun.llm.local_driver.AutoTokenizer')
    @patch('mahoun.llm.local_driver.AutoModelForCausalLM')
    def test_generate_without_loading(self, mock_model_class, mock_tokenizer_class, tmp_path):
        """Test generation without loading model raises error"""
        driver = LocalLLMDriver(model_dir=str(tmp_path))
        
        with pytest.raises(RuntimeError) as exc_info:
            driver.generate("test prompt")
        
        assert "not loaded" in str(exc_info.value).lower()
    
    @patch('mahoun.llm.local_driver.AutoTokenizer')
    @patch('mahoun.llm.local_driver.AutoModelForCausalLM')
    @patch('mahoun.llm.local_driver.torch')
    def test_generate_success(self, mock_torch, mock_model_class, mock_tokenizer_class, tmp_path):
        """Test successful text generation"""
        # Setup
        model_dir = tmp_path / "test-model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}")
        
        # Mock tokenizer
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = "<pad>"
        mock_tokenizer.eos_token = "<eos>"
        mock_tokenizer.pad_token_id = 0
        mock_tokenizer.eos_token_id = 1
        
        mock_inputs = {"input_ids": torch.tensor([[1, 2, 3]])}
        mock_tokenizer.return_value = mock_inputs
        mock_tokenizer.decode.return_value = "Generated text"
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        # Mock model
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_output = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model.generate.return_value = mock_output
        mock_model_class.from_pretrained.return_value = mock_model
        
        # Mock torch
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = Mock()
        mock_torch.no_grad.return_value.__exit__ = Mock()
        
        # Load and generate
        driver = LocalLLMDriver(
            model_dir=str(tmp_path),
            use_quantization=False,
            device="cpu"
        )
        driver.load("test-model")
        
        result = driver.generate("test prompt")
        
        # Verify
        assert isinstance(result, str)
        assert driver.metrics.total_generations == 1
        assert driver.metrics.total_tokens_generated > 0
    
    @patch('mahoun.llm.local_driver.AutoTokenizer')
    @patch('mahoun.llm.local_driver.AutoModelForCausalLM')
    @patch('mahoun.llm.local_driver.torch')
    def test_generate_with_metrics(self, mock_torch, mock_model_class, mock_tokenizer_class, tmp_path):
        """Test generation with metrics return"""
        # Setup (similar to above)
        model_dir = tmp_path / "test-model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}")
        
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = "<pad>"
        mock_tokenizer.eos_token = "<eos>"
        mock_tokenizer.pad_token_id = 0
        mock_tokenizer.eos_token_id = 1
        mock_tokenizer.return_value = {"input_ids": torch.tensor([[1, 2, 3]])}
        mock_tokenizer.decode.return_value = "Generated text"
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        mock_model = Mock()
        mock_model.device = "cpu"
        mock_model.generate.return_value = torch.tensor([[1, 2, 3, 4, 5]])
        mock_model_class.from_pretrained.return_value = mock_model
        
        mock_torch.cuda.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = Mock()
        mock_torch.no_grad.return_value.__exit__ = Mock()
        
        # Load and generate
        driver = LocalLLMDriver(model_dir=str(tmp_path), use_quantization=False)
        driver.load("test-model")
        
        result = driver.generate("test prompt", return_metrics=True)
        
        # Verify
        assert isinstance(result, dict)
        assert "text" in result
        assert "metrics" in result
        assert "generation_time" in result["metrics"]
        assert "tokens_generated" in result["metrics"]
        assert "tokens_per_second" in result["metrics"]
    
    def test_generation_config_defaults(self):
        """Test GenerationConfig default values"""
        config = GenerationConfig()
        
        assert config.max_new_tokens == 1024
        assert config.temperature == 0.4
        assert config.top_p == 0.9
        assert config.top_k == 50
        assert config.do_sample is True
    
    def test_list_available_models(self, tmp_path):
        """Test listing available models"""
        # Create some model directories
        (tmp_path / "model1").mkdir()
        (tmp_path / "model2").mkdir()
        (tmp_path / ".hidden").mkdir()  # Should be ignored
        (tmp_path / "file.txt").write_text("test")  # Should be ignored
        
        driver = LocalLLMDriver(model_dir=str(tmp_path))
        models = driver._list_available_models()
        
        assert len(models) == 2
        assert "model1" in models
        assert "model2" in models
        assert ".hidden" not in models
    
    @patch('mahoun.llm.local_driver.AutoTokenizer')
    @patch('mahoun.llm.local_driver.AutoModelForCausalLM')
    @patch('mahoun.llm.local_driver.torch')
    def test_unload_model(self, mock_torch, mock_model_class, mock_tokenizer_class, tmp_path):
        """Test model unloading and memory cleanup"""
        model_dir = tmp_path / "test-model"
        model_dir.mkdir()
        (model_dir / "config.json").write_text("{}")
        
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = "<pad>"
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        
        mock_model = Mock()
        mock_model_class.from_pretrained.return_value = mock_model
        
        mock_torch.cuda.is_available.return_value = False
        
        driver = LocalLLMDriver(model_dir=str(tmp_path), use_quantization=False)
        driver.load("test-model")
        
        assert driver.model is not None
        assert driver.tokenizer is not None
        
        driver.unload()
        
        assert driver.model is None
        assert driver.tokenizer is None
    
    def test_get_metrics(self, tmp_path):
        """Test metrics retrieval"""
        driver = LocalLLMDriver(model_dir=str(tmp_path))
        driver.model_name = "test-model"
        driver.metrics.load_time_seconds = 5.0
        driver.metrics.total_generations = 10
        
        metrics = driver.get_metrics()
        
        assert metrics["model_name"] == "test-model"
        assert metrics["load_time_seconds"] == 5.0
        assert metrics["total_generations"] == 10
    
    def test_repr(self, tmp_path):
        """Test string representation"""
        driver = LocalLLMDriver(model_dir=str(tmp_path))
        
        repr_str = repr(driver)
        assert "LocalLLMDriver" in repr_str
        assert "not loaded" in repr_str
        
        driver.model_name = "test-model"
        driver.model = Mock()
        
        repr_str = repr(driver)
        assert "test-model" in repr_str
        assert "loaded" in repr_str


@pytest.mark.integration
class TestLocalLLMDriverIntegration:
    """Integration tests (require actual model)"""
    
    @pytest.mark.skip(reason="Requires actual model download")
    def test_real_model_loading(self):
        """Test with real model (manual test)"""
        driver = LocalLLMDriver(
            model_dir="./models",
            use_quantization=True
        )
        
        # This would require an actual model to be present
        # driver.load("llama-3.2-1b-instruct")
        # result = driver.generate("Hello, world!")
        # assert len(result) > 0
        pass
