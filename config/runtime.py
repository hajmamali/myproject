import json
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    provider: str
    model_path: str
    default_model: str
    max_tokens: int
    temperature: float
    use_gpu: bool
    gpu_memory_fraction: float

@dataclass
class RuntimeConfigData:
    mode: str
    environment: str
    lora_enabled: bool
    graph_enabled: bool
    llm: LLMConfig

class RuntimeConfig:
    _instance = None

    @classmethod
    def load(cls) -> RuntimeConfigData:
        config_path = os.path.join(os.path.dirname(__file__), "runtime.json")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Runtime config not found at {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        return RuntimeConfigData(
            mode=data.get("mode"),
            environment=data.get("environment"),
            lora_enabled=data.get("lora_enabled"),
            graph_enabled=data.get("graph_enabled"),
            llm=LLMConfig(**data.get("llm", {}))
        )
