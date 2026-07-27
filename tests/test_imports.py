#!/usr/bin/env python3

try:
    from mahoun.core.models import AIResponse
    print('✅ AIResponse import successful')
except Exception as e:
    print(f'❌ AIResponse import failed: {e}')

try:
    from mahoun.core.models import AuditEvent
    print('✅ AuditEvent import successful')
except Exception as e:
    print(f'❌ AuditEvent import failed: {e}')

try:
    from mahoun.core.models import DeploymentProfile
    print('✅ DeploymentProfile import successful')
except Exception as e:
    print(f'❌ DeploymentProfile import failed: {e}')

try:
    from mahoun.core.models import Entity
    print('✅ Entity import successful')
except Exception as e:
    print(f'❌ Entity import failed: {e}')

try:
    from mahoun.core.models import ReasoningStep
    print('✅ ReasoningStep import successful')
except Exception as e:
    print(f'❌ ReasoningStep import failed: {e}')

print('Import test complete!')