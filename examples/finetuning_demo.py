#!/usr/bin/env python3
"""
Fine-Tuning Demo
================
Demonstrates the complete fine-tuning pipeline with model registry.

This example shows:
1. Creating a training dataset from documents
2. Starting a fine-tuning job
3. Tracking models in the registry
4. Querying best models by domain/metrics
"""

import asyncio
from pathlib import Path

from mahoun.finetuning import (
    TrainingManager,
    ModelRegistry,
    get_registry,
)
from mahoun.finetuning.config import DocumentToTrainingConfig


async def main():
    print("=" * 70)
    print("Mahoun Fine-Tuning Pipeline Demo")
    print("=" * 70)
    print()
    
    # 1. Initialize components
    print("📦 Initializing components...")
    config = DocumentToTrainingConfig()
    registry = get_registry()  # Singleton registry
    trainer = TrainingManager(config=config, registry=registry)
    print(f"✅ Registry loaded: {len(registry.list_models())} existing models")
    print()
    
    # 2. Show registry statistics
    print("📊 Registry Statistics:")
    stats = registry.get_statistics()
    print(f"   Total models: {stats['total_models']}")
    print(f"   By domain: {stats['by_domain']}")
    print(f"   By status: {stats['by_status']}")
    print()
    
    # 3. List models by domain
    print("🔍 Models by domain:")
    for domain in ["legal", "medical", "general"]:
        models = registry.list_models(domain=domain, status="completed")
        print(f"   {domain}: {len(models)} models")
        
        if models:
            # Show best model for this domain
            best = registry.get_best_model(metric="final_loss", domain=domain)
            if best:
                print(f"      Best: {best.job_id} (loss={best.metrics.get('final_loss', 'N/A')})")
    print()
    
    # 4. Example: Start a new training job (commented out - requires actual dataset)
    print("💡 Example: Starting a training job")
    print("   (Commented out - requires actual dataset)")
    print()
    print("   Code:")
    print("   ```python")
    print("   job_id = await trainer.start_training_job(")
    print("       dataset_path='./datasets/legal_qa',")
    print("       base_model_name='unsloth/llama-3-8b-bnb-4bit',")
    print("       domain='legal',")
    print("       tags=['contracts', 'iranian-law']")
    print("   )")
    print("   ```")
    print()
    
    # 5. Query models
    print("🔎 Query Examples:")
    
    # Get all completed models
    completed = registry.list_models(status="completed")
    print(f"   Completed models: {len(completed)}")
    
    # Get best model overall
    best_overall = registry.get_best_model(metric="final_loss")
    if best_overall:
        print(f"   Best model (by loss): {best_overall.job_id}")
        print(f"      Domain: {best_overall.domain}")
        print(f"      Loss: {best_overall.metrics.get('final_loss', 'N/A')}")
        print(f"      GGUF exports: {list(best_overall.gguf_paths.keys())}")
    else:
        print("   No completed models found")
    print()
    
    # 6. Export summary
    summary_path = "./models/registry_summary.md"
    print(f"📄 Exporting registry summary to {summary_path}...")
    registry.export_summary(summary_path)
    print("✅ Summary exported")
    print()
    
    # 7. Show usage patterns
    print("📚 Common Usage Patterns:")
    print()
    print("   # Get specific model")
    print("   model = registry.get_model('job_20250213_120000')")
    print()
    print("   # List models with tags")
    print("   models = registry.list_models(tags=['contracts'])")
    print()
    print("   # Get best model for domain")
    print("   best = registry.get_best_model(metric='final_loss', domain='legal')")
    print()
    print("   # Update model metrics after evaluation")
    print("   registry.update_metrics('job_id', {'accuracy': 0.95})")
    print()
    print("   # Add GGUF export path")
    print("   registry.add_gguf_path('job_id', 'q4_k_m', './path/to/model.gguf')")
    print()
    
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
