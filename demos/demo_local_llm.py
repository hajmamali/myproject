#!/usr/bin/env python3
"""
Local LLM Demo
==============
Demonstrate local LLM capabilities with the LocalLLMDriver.

This script shows:
- Model loading
- Text generation
- Batch processing
- Performance metrics
- Error handling
"""

import sys
import logging
import time
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from mahoun.llm.local_driver import LocalLLMDriver, GenerationConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def load_runtime_config():
    try:
        config_path = Path("config/runtime.json")
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Could not load runtime.json: {e}")
    return None

def main():
    """Run local LLM demo"""
    
    print("=" * 80)
    print("🤖 MAHOUN Local LLM Demo")
    print("=" * 80)
    print()
    
    # Load Config
    config = load_runtime_config()
    model_dir = "./models"
    model_name = None
    use_gpu = False # Default safety

    if config and "llm" in config:
        llm_config = config["llm"]
        model_dir = llm_config.get("model_path", "./models")
        model_name = llm_config.get("default_model")
        use_gpu = llm_config.get("use_gpu", False)
        print(f"⚙️  Configuration Loaded from runtime.json:")
        print(f"   Model Path: {model_dir}")
        print(f"   Target Model: {model_name}")
        print(f"   Use GPU: {use_gpu}")
    else:
        print("⚠️  No runtime.json found, using defaults.")

    print(f"\n📦 Initializing LocalLLMDriver at '{model_dir}'...")
    
    try:
        driver = LocalLLMDriver(
            model_dir=model_dir,
            use_quantization=True,  # Always try optimization
            device="cuda" if use_gpu else "cpu",
            max_memory_gb=2.0 # Safety limit for old laptop
        )
    except Exception as e:
         print(f"❌ Failed to initialize driver: {e}")
         return

    available_models = driver._list_available_models()
    
    # If we have a specific model file pointing to GGUF, we might not list it same way
    # but let's see.
    
    # Logic Update: If we have a specific model_name Configured, try to load IT directly
    if model_name:
         print(f"\n🚀 Attempting to load configured model: {model_name}")
         try:
             driver.load(model_name)
         except Exception as e:
             print(f"❌ Failed to load configured model: {e}")
             print("\nAvailable models in directory:")
             for m in available_models:
                 print(f" - {m}")
             return
    elif not available_models:
        print(f"\n❌ No models found in {model_dir}")
        print("\n📥 To download a model, run:")
        print("   huggingface-cli download Qwen/Qwen2.5-0.5B-Instruct --local-dir ./models/qwen-2.5-0.5b-instruct")
        return
    else:
        # Fallback to interactive selection if no default set
        print(f"\n📋 Available Models in {model_dir}:")
        for i, m in enumerate(available_models):
            print(f"{i+1}. {m}")
        
        # Default to first if not interactive
        model_name = available_models[0]
        print(f"\n🚀 Loading first available model: {model_name}")
        driver.load(model_name)
    print()
    
    # Test single generation
    prompt = "What is the capital of France? Answer in one sentence."
    print(f"Prompt: {prompt}")
    print()
    
    config = GenerationConfig(
        max_new_tokens=100,
        temperature=0.7,
        top_p=0.9
    )
    
    try:
        result = driver.generate(prompt, config, return_metrics=True)
        print(f"Generated: {result['text']}")
        print()
        print(f"⚡ Metrics:")
        print(f"   Generation time: {result['metrics']['generation_time']:.2f}s")
        print(f"   Tokens generated: {result['metrics']['tokens_generated']}")
        print(f"   Tokens/second: {result['metrics']['tokens_per_second']:.2f}")
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        return
    
    print()
    print("-" * 80)
    print("📚 Batch Generation Test")
    print("-" * 80)
    print()
    
    # Test batch generation
    prompts = [
        "What is 2+2?",
        "Name a programming language.",
        "What color is the sky?"
    ]
    
    print(f"Processing {len(prompts)} prompts...")
    print()
    
    try:
        results = driver.batch_generate(prompts, config)
        for i, (prompt, result) in enumerate(zip(prompts, results), 1):
            print(f"{i}. Prompt: {prompt}")
            print(f"   Result: {result[:100]}...")
            print()
    except Exception as e:
        print(f"❌ Batch generation failed: {e}")
    
    print()
    print("-" * 80)
    print("📊 Performance Metrics")
    print("-" * 80)
    print()
    
    metrics = driver.get_metrics()
    print(f"Model: {metrics['model_name']}")
    print(f"Load time: {metrics['load_time_seconds']:.2f}s")
    print(f"Total generations: {metrics['total_generations']}")
    print(f"Total tokens: {metrics['total_tokens_generated']}")
    print(f"Avg generation time: {metrics['avg_generation_time']:.2f}s")
    print(f"Memory usage: {metrics['memory_usage_mb']:.2f} MB")
    
    print()
    print("-" * 80)
    print("🧹 Cleanup")
    print("-" * 80)
    print()
    
    driver.unload()
    
    print()
    print("=" * 80)
    print("✅ Demo completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    main()
