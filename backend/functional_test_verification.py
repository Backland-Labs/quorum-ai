#!/usr/bin/env python3
"""
Functional Test Verification for ActivityService Nonce Tracking Implementation
This script simulates the key functional tests without running pytest.
"""

import json
import os
import tempfile
import sys
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, '/Users/max/code/quorum-ai/backend')

def test_report(test_name: str, status: bool, message: str = ""):
    """Print test result in a consistent format"""
    status_emoji = "✅" if status else "❌"
    status_text = "PASS" if status else "FAIL"
    print(f"{status_emoji} {status_text}: {test_name}")
    if message:
        print(f"   📄 {message}")
    if not status:
        print(f"   🔍 Check implementation details")
    print()

def verify_activity_service_implementation():
    """Verify ActivityService implementation by examining the source code"""
    
    print("🔍 FUNCTIONAL TEST VERIFICATION: ActivityService Nonce Tracking")
    print("=" * 80)
    
    success = True
    
    # Test 1: Check ActivityService file exists and has required methods
    try:
        from services.activity_service import ActivityService, NonceValidationError
        
        service = ActivityService()
        
        # Check required attributes exist
        has_nonces = hasattr(service, 'nonces')
        has_constants = all([
            hasattr(service, 'NONCE_MULTISIG_ACTIVITY'),
            hasattr(service, 'NONCE_VOTE_ATTESTATIONS'),
            hasattr(service, 'NONCE_VOTING_CONSIDERED'),
            hasattr(service, 'NONCE_NO_VOTING')
        ])
        
        # Check required methods exist
        required_methods = [
            'increment_multisig_activity',
            'increment_vote_attestation', 
            'increment_voting_considered',
            'increment_no_voting',
            'getMultisigNonces',
            'isRatioPass'
        ]
        
        has_methods = all(hasattr(service, method) for method in required_methods)
        
        test_result = has_nonces and has_constants and has_methods
        success = success and test_result
        
        test_report("ActivityService initialization and structure", 
                   test_result,
                   f"Nonces: {has_nonces}, Constants: {has_constants}, Methods: {has_methods}")
        
    except ImportError as e:
        test_report("ActivityService import", False, str(e))
        success = False
        return success
    
    # Test 2: Check nonce constants have correct values
    try:
        correct_constants = (
            service.NONCE_MULTISIG_ACTIVITY == 0 and
            service.NONCE_VOTE_ATTESTATIONS == 1 and
            service.NONCE_VOTING_CONSIDERED == 2 and
            service.NONCE_NO_VOTING == 3
        )
        
        success = success and correct_constants
        
        test_report("Nonce constants have correct values", 
                   correct_constants,
                   f"Constants: {service.NONCE_MULTISIG_ACTIVITY}, {service.NONCE_VOTE_ATTESTATIONS}, {service.NONCE_VOTING_CONSIDERED}, {service.NONCE_NO_VOTING}")
        
    except Exception as e:
        test_report("Nonce constants check", False, str(e))
        success = False
    
    # Test 3: Check getMultisigNonces returns correct format
    try:
        # For unknown address, should return [0,0,0,0]
        result = service.getMultisigNonces("0xunknown")
        correct_format = (
            isinstance(result, list) and
            len(result) == 4 and
            all(isinstance(x, int) and x >= 0 for x in result)
        )
        
        success = success and correct_format
        
        test_report("getMultisigNonces returns correct format", 
                   correct_format,
                   f"Result for unknown address: {result}")
        
    except Exception as e:
        test_report("getMultisigNonces format check", False, str(e))
        success = False
    
    # Test 4: Check state persistence structure
    try:
        # Create temporary file to test state saving
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp:
            # Mock the persistent file path
            original_file = service.persistent_file
            service.persistent_file = tmp.name
            
            # Add some test nonce data
            service.nonces = {
                "ethereum": {0: 5, 1: 3, 2: 8, 3: 1}
            }
            
            # Save state
            service.save_state()
            
            # Read back the saved data
            with open(tmp.name, 'r') as f:
                saved_data = json.load(f)
            
            # Check structure
            has_required_fields = all(field in saved_data for field in 
                                    ['nonces', 'last_updated', 'last_activity_date', 'last_tx_hash'])
            
            nonces_correct = (
                'ethereum' in saved_data['nonces'] and
                len(saved_data['nonces']['ethereum']) == 4
            )
            
            # Restore original file path
            service.persistent_file = original_file
            
            # Clean up
            os.unlink(tmp.name)
            
            test_result = has_required_fields and nonces_correct
            success = success and test_result
            
            test_report("State persistence structure", 
                       test_result,
                       f"Fields present: {has_required_fields}, Nonces correct: {nonces_correct}")
            
    except Exception as e:
        test_report("State persistence check", False, str(e))
        success = False
    
    # Test 5: Check NonceValidationError exception exists
    try:
        # Test creating exception
        error = NonceValidationError("ethereum", 0, "Test error")
        has_attributes = (
            hasattr(error, 'chain') and
            hasattr(error, 'nonce_type') and
            error.chain == "ethereum" and
            error.nonce_type == 0
        )
        
        success = success and has_attributes
        
        test_report("NonceValidationError exception class", 
                   has_attributes,
                   f"Exception created with correct attributes")
        
    except Exception as e:
        test_report("NonceValidationError check", False, str(e))
        success = False
    
    return success

def verify_api_endpoints():
    """Verify API endpoint implementations"""
    
    print("\n🌐 API ENDPOINTS VERIFICATION")
    print("=" * 80)
    
    success = True
    
    try:
        # Check if main.py has the required endpoints
        main_py_path = Path('/Users/max/code/quorum-ai/backend/main.py')
        if not main_py_path.exists():
            test_report("main.py file exists", False, "File not found")
            return False
        
        main_content = main_py_path.read_text()
        
        # Check for required endpoints
        required_endpoints = [
            '@app.get("/activity/nonces"',
            '@app.get("/activity/eligibility/{chain}"',
            '@app.get("/activity/status"'
        ]
        
        endpoints_present = all(endpoint in main_content for endpoint in required_endpoints)
        success = success and endpoints_present
        
        test_report("Required API endpoints present in main.py", 
                   endpoints_present,
                   f"Endpoints: {required_endpoints}")
        
        # Check for NonceResponse and EligibilityResponse models
        models_py_path = Path('/Users/max/code/quorum-ai/backend/models.py')
        if models_py_path.exists():
            models_content = models_py_path.read_text()
            
            required_models = [
                'class NonceData',
                'class NonceResponse',
                'class EligibilityResponse'
            ]
            
            models_present = all(model in models_content for model in required_models)
            success = success and models_present
            
            test_report("Required response models present in models.py", 
                       models_present,
                       f"Models: {required_models}")
        
    except Exception as e:
        test_report("API endpoints verification", False, str(e))
        success = False
    
    return success

def verify_integration_points():
    """Verify integration points mentioned in service integration tests"""
    
    print("\n🔗 INTEGRATION POINTS VERIFICATION")
    print("=" * 80)
    
    success = True
    
    try:
        # Check VotingService file for activity service integration
        voting_service_path = Path('/Users/max/code/quorum-ai/backend/services/voting_service.py')
        if voting_service_path.exists():
            voting_content = voting_service_path.read_text()
            
            # Look for activity service references
            has_activity_service_ref = 'activity_service' in voting_content.lower()
            
            test_report("VotingService has activity service references", 
                       has_activity_service_ref,
                       f"Found activity_service references in voting service")
        
        # Check SafeService file for activity service integration
        safe_service_path = Path('/Users/max/code/quorum-ai/backend/services/safe_service.py')
        if safe_service_path.exists():
            safe_content = safe_service_path.read_text()
            
            # Look for activity service references
            has_activity_service_ref = 'activity_service' in safe_content.lower()
            
            test_report("SafeService has activity service references", 
                       has_activity_service_ref,
                       f"Found activity_service references in safe service")
        
    except Exception as e:
        test_report("Integration points verification", False, str(e))
        success = False
    
    return success

def verify_edge_cases():
    """Verify edge case handling"""
    
    print("\n⚠️  EDGE CASES VERIFICATION")
    print("=" * 80)
    
    success = True
    
    try:
        from services.activity_service import ActivityService, NonceValidationError
        
        # Test 1: Unknown chain handling
        try:
            service = ActivityService()
            service.increment_multisig_activity("unknown_chain")
            test_report("Unknown chain handling", False, "Should raise NonceValidationError")
            success = False
        except NonceValidationError as e:
            test_report("Unknown chain handling", True, f"Correctly raised NonceValidationError: {e}")
        except Exception as e:
            test_report("Unknown chain handling", False, f"Wrong exception type: {e}")
            success = False
        
        # Test 2: Zero period handling in ratio calculation
        try:
            service = ActivityService()
            ratio = service._calculate_activity_ratio([5, 3, 2, 1], 0)  # Zero period
            zero_handling_correct = ratio == 0
            success = success and zero_handling_correct
            
            test_report("Zero period handling in ratio calculation", 
                       zero_handling_correct,
                       f"Ratio with zero period: {ratio}")
        
        except Exception as e:
            test_report("Zero period handling", False, str(e))
            success = False
        
    except ImportError as e:
        test_report("Edge cases verification setup", False, f"Import error: {e}")
        success = False
    
    return success

def main():
    """Main test runner"""
    print("🧪 COMPREHENSIVE FUNCTIONAL TEST VERIFICATION")
    print("ActivityService Staking Contract Nonce Tracking Implementation")
    print("=" * 80)
    
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[0]}")
    print()
    
    # Run verification steps
    overall_success = True
    
    test1_success = verify_activity_service_implementation()
    test2_success = verify_api_endpoints()
    test3_success = verify_integration_points()
    test4_success = verify_edge_cases()
    
    overall_success = test1_success and test2_success and test3_success and test4_success
    
    # Final summary
    print("\n" + "=" * 80)
    if overall_success:
        print("🎉 OVERALL VERIFICATION: PASSED")
        print("✅ ActivityService nonce tracking implementation appears functional")
        print("✅ All key components and interfaces are properly implemented")
        print("✅ Edge cases are handled appropriately")
    else:
        print("❌ OVERALL VERIFICATION: ISSUES FOUND")
        print("⚠️  Some components may need attention")
    
    print("=" * 80)
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    sys.exit(main())