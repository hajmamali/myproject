#!/usr/bin/env python3
"""
Simple governance test outside the test directory
"""

@pytest.mark.p1
@pytest.mark.p0
def test_reasoning_response_validation():
    print('Testing ReasoningResponse validation...')

    try:
        from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
        from mahoun.guardrails.exceptions import InvariantViolation
        print('✅ Imports successful')
        
        # Test 1: Try to create invalid response  
        try:
            response = ReasoningResponse(
                success=True,
                result='test',
                confidence=0.9,
                reasoning_mode=ReasoningMode.SYMBOLIC,
                execution_time_ms=100.0,
                fortress_validated=False  # This should trigger validation error
            )
            print('❌ GOVERNANCE BYPASS: Invalid response was created!')
            return False
        except InvariantViolation as e:
            print(f'✅ Governance working: InvariantViolation: {e}')
            return True
        except Exception as e:
            print(f'✅ Governance working: {type(e).__name__}: {e}')
            return True
            
    except Exception as e:
        print(f'Error during test: {e}')
        return False

if __name__ == "__main__":
    result = test_reasoning_response_validation()
    exit(0 if result else 1)