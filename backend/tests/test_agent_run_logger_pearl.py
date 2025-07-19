"""
Tests for Pearl-compliant AgentRunLogger service.

This module tests the migration of AgentRunLogger from Logfire to Pearl-compliant logging.
The AgentRunLogger must produce audit trail logs in Pearl format for autonomous agent monitoring.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock
from datetime import datetime

from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    UserPreferences,
    VoteDecision,
    VotingStrategy,
    RiskLevel,
    VoteType
)


class TestAgentRunLoggerPearlCompliance:
    """
    Test AgentRunLogger produces Pearl-compliant audit trail logs.
    
    This test validates that the migrated AgentRunLogger service produces logs in the exact
    Pearl format required for autonomous agent monitoring and debugging on Pearl platform.
    """
    
    def teardown_method(self):
        """Clean up loggers after each test to avoid conflicts."""
        import logging
        # Clear all handlers from loggers to avoid conflicts
        for name in ['agent', 'agent_run_logger']:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_agent_run_logger_initialization(self):
        """
        Test that AgentRunLogger initializes correctly with Pearl-compliant logging.
        
        This test validates that the migrated logger properly initializes with Pearl logger
        configuration instead of Logfire. Critical for autonomous agent deployment.
        """
        # This will fail until we implement Pearl-compliant AgentRunLogger
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            assert logger.start_time is None
            assert logger.run_id is None
            assert os.path.exists(log_file)  # Should initialize log file
    
    def test_log_agent_start_pearl_format(self):
        """
        Test log_agent_start produces Pearl-compliant audit trail logs.
        
        This test validates that agent run initiation is logged in Pearl format with all
        required parameters for compliance monitoring. Essential for agent audit trails.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Create test data
            request = AgentRunRequest(
                space_id="test-space",
                dry_run=False
            )
            preferences = UserPreferences(
                voting_strategy=VotingStrategy.BALANCED,
                confidence_threshold=0.7,
                max_proposals_per_run=5
            )
            
            logger.log_agent_start(request, preferences)
            
            # Verify Pearl-compliant log was written
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Should contain Pearl-formatted log entry
            assert '[INFO] [agent] Agent run started' in content
            assert 'space_id=test-space' in content
            assert 'dry_run=False' in content
            assert 'strategy=balanced' in content
            assert 'confidence_threshold=0.7' in content
    
    def test_log_proposals_fetched_audit_trail(self):
        """
        Test log_proposals_fetched creates proper audit trail in Pearl format.
        
        This test validates that proposal fetching results are logged with all necessary
        information for compliance audit trails. Critical for tracking agent decisions.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=True)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Create test proposals
            proposals = [
                Proposal(
                    id="prop1",
                    title="Test Proposal 1",
                    choices=["For", "Against"],
                    start=1698768000,
                    end=1699372800,
                    state="active",
                    author="0x123",
                    network="1",
                    symbol="TEST",
                    scores=[100.0, 50.0],
                    scores_total=150.0,
                    votes=10,
                    created=1698681600,
                    quorum=10.0,
                    body="Test proposal 1 description"
                ),
                Proposal(
                    id="prop2",
                    title="Test Proposal 2",
                    choices=["For", "Against"],
                    start=1698768000,
                    end=1699372800,
                    state="active",
                    author="0x456",
                    network="1",
                    symbol="TEST",
                    scores=[200.0, 25.0],
                    scores_total=225.0,
                    votes=15,
                    created=1698681600,
                    quorum=10.0,
                    body="Test proposal 2 description"
                )
            ]
            
            logger.log_proposals_fetched(proposals, 10)
            
            # Verify audit trail
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[INFO] [agent] Proposals fetched and filtered' in content
            assert 'total_proposals=2' in content
            assert 'filtered_proposals=10' in content
            assert 'prop1,prop2' in content  # Should log proposal IDs
    
    def test_log_proposal_analysis_decision_tracking(self):
        """
        Test log_proposal_analysis tracks individual proposal decisions in Pearl format.
        
        This test validates that each proposal analysis and voting decision is properly
        logged for compliance monitoring. Essential for autonomous agent accountability.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=True)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Create test proposal and decision
            proposal = Proposal(
                id="test-proposal",
                title="Very Long Proposal Title That Should Be Truncated For Log Readability",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x789",
                network="1",
                symbol="TEST",
                scores=[150.0, 75.0],
                scores_total=225.0,
                votes=12,
                created=1698681600,
                quorum=10.0,
                body="Test proposal description"
            )
            decision = VoteDecision(
                proposal_id="test-proposal",
                vote=VoteType.FOR,
                confidence=0.85,
                reasoning="Test reasoning for this proposal analysis",
                strategy_used=VotingStrategy.BALANCED,
                risk_assessment=RiskLevel.LOW,
                estimated_gas_cost=0.005
            )
            
            logger.log_proposal_analysis(proposal, decision)
            
            # Verify decision tracking
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[INFO] [agent] Proposal analyzed' in content
            assert 'proposal_id=test-proposal' in content
            assert 'vote_choice=VoteType.FOR' in content
            assert 'confidence=0.85' in content
            assert 'risk_level=LOW' in content
            # Title should be truncated to 100 chars
            assert 'Very Long Proposal Title That Should Be Truncated For Log Readability'[:100] in content
    
    def test_log_vote_execution_success_audit(self):
        """
        Test log_vote_execution creates proper audit trail for successful votes.
        
        This test validates that successful vote executions are logged with all required
        information for compliance auditing. Critical for tracking agent actions.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=False)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Create test decision
            decision = VoteDecision(
                proposal_id="test-proposal",
                vote=VoteType.FOR,
                confidence=0.9,
                reasoning="High confidence vote decision",
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=0.005
            )
            
            logger.log_vote_execution(decision, success=True)
            
            # Verify success audit
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[INFO] [agent] Vote executed successfully' in content
            assert 'proposal_id=test-proposal' in content
            assert 'vote_choice=VoteType.FOR' in content
            assert 'confidence=0.9' in content
    
    def test_log_vote_execution_failure_audit(self):
        """
        Test log_vote_execution creates proper audit trail for failed votes.
        
        This test validates that failed vote executions are logged with error details
        for debugging and compliance monitoring. Critical for error tracking.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=False)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Create test decision
            decision = VoteDecision(
                proposal_id="test-proposal",
                vote=VoteType.FOR,
                confidence=0.9,
                reasoning="Vote execution test decision",
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=0.005
            )
            
            logger.log_vote_execution(decision, success=False, error="Network timeout")
            
            # Verify failure audit
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[ERROR] [agent] Vote execution failed' in content
            assert 'proposal_id=test-proposal' in content
            assert 'vote_choice=VoteType.FOR' in content
            assert 'error=Network timeout' in content
    
    def test_log_agent_completion_summary_metrics(self):
        """
        Test log_agent_completion creates comprehensive run summary in Pearl format.
        
        This test validates that agent run completion is logged with all summary metrics
        for performance monitoring and compliance reporting. Essential for agent oversight.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=False)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Simulate some execution time
            time.sleep(0.01)
            
            # Create test response
            response = AgentRunResponse(
                space_id="test-space",
                proposals_analyzed=3,
                votes_cast=[
                    VoteDecision(
                        proposal_id="prop1",
                        vote=VoteType.FOR,
                        confidence=0.8,
                        reasoning="Supporting this proposal",
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.005
                    ),
                    VoteDecision(
                        proposal_id="prop2",
                        vote=VoteType.AGAINST,
                        confidence=0.7,
                        reasoning="Opposing this proposal",
                        strategy_used=VotingStrategy.BALANCED,
                        estimated_gas_cost=0.005
                    )
                ],
                user_preferences_applied=True,
                execution_time=2.5,
                errors=["Minor error during processing"]
            )
            
            logger.log_agent_completion(response)
            
            # Verify completion summary
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[INFO] [agent] Agent run completed' in content
            assert 'space_id=test-space' in content
            assert 'proposals_analyzed=3' in content
            assert 'votes_cast=2' in content
            assert 'successful_votes=2' in content
            assert 'execution_time=' in content
            assert 'errors=' in content
    
    def test_log_error_with_context_tracking(self):
        """
        Test log_error properly logs errors with context in Pearl format.
        
        This test validates that agent errors are logged with sufficient context
        for debugging while maintaining Pearl compliance. Critical for error resolution.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=False)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Log test error
            test_error = ValueError("Test error message")
            logger.log_error("proposal_analysis", test_error, proposal_id="test-prop")
            
            # Verify error logging
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[ERROR] [agent] Agent run proposal_analysis failed' in content
            assert 'operation=proposal_analysis' in content
            assert 'error=Test error message' in content
            assert 'error_type=ValueError' in content
            assert 'proposal_id=test-prop' in content
    
    def test_log_security_event_sanitized_logging(self):
        """
        Test log_security_event properly sanitizes sensitive data while logging security events.
        
        This test validates that security events are logged with proper data sanitization,
        ensuring no sensitive information leaks while maintaining security monitoring capabilities.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=False)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Log security event with sensitive data
            security_details = {
                "transaction_hash": "0x123abc",
                "private_key": "super_secret_key",  # Should be filtered out
                "api_key": "secret_api_key",  # Should be filtered out
                "user_address": "0x456def",
                "token": "secret_token"  # Should be filtered out
            }
            
            logger.log_security_event("suspicious_transaction", security_details)
            
            # Verify security event logging
            with open(log_file, 'r') as f:
                content = f.read()
            
            assert '[WARN] [agent] Security event: suspicious_transaction' in content
            assert 'transaction_hash=0x123abc' in content
            assert 'user_address=0x456def' in content
            # Sensitive data should NOT be present
            assert 'super_secret_key' not in content
            assert 'secret_api_key' not in content
            assert 'secret_token' not in content


class TestAgentRunLoggerPearlIntegration:
    """
    Test AgentRunLogger integration with Pearl logging infrastructure.
    
    These tests validate that the migrated logger properly integrates with the Pearl-compliant
    logging infrastructure and produces audit trails in the correct format.
    """
    
    def teardown_method(self):
        """Clean up loggers after each test to avoid conflicts."""
        import logging
        # Clear all handlers from loggers to avoid conflicts
        for name in ['agent', 'agent_run_logger']:
            logger = logging.getLogger(name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
    
    def test_agent_run_logger_uses_pearl_formatter(self):
        """
        Test that AgentRunLogger uses PearlFormatter for all log messages.
        
        This test validates that all log messages produced by the migrated logger
        conform to Pearl timestamp and format requirements. Critical for platform compliance.
        """
        from services.agent_run_logger import AgentRunLogger
        from logging_config import validate_log_format
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize and perform various logging operations
            request = AgentRunRequest(space_id="test-space", dry_run=True)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            proposals = [Proposal(
                id="prop1",
                title="Test",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0,
                body="Test proposal description"
            )]
            logger.log_proposals_fetched(proposals, 5)
            
            # Read all log lines and validate Pearl format
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            # Filter out initialization line and validate all agent run lines
            agent_run_lines = [line.strip() for line in lines if 'Agent run' in line or 'Proposals fetched' in line]
            
            for line in agent_run_lines:
                assert validate_log_format(line), f"Log line doesn't match Pearl format: {line}"
    
    def test_agent_run_logger_respects_pearl_store_path(self):
        """
        Test that AgentRunLogger respects Pearl STORE_PATH environment variable.
        
        This test validates that the logger correctly uses Pearl's storage path
        for log file location when deployed on Pearl platform.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, 'pearl_store')
            os.makedirs(store_path)
            
            # Test with store_path parameter (simulating Pearl environment)
            logger = AgentRunLogger(store_path=store_path)
            
            expected_log_file = os.path.join(store_path, 'log.txt')
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=True)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Verify log file was created in correct location
            assert os.path.exists(expected_log_file)
            
            with open(expected_log_file, 'r') as f:
                content = f.read()
                assert '[INFO] [agent] Agent run started' in content
    
    def test_agent_run_logger_preserves_run_id_context(self):
        """
        Test that AgentRunLogger preserves run_id context across all log messages.
        
        This test validates that all log messages within a single agent run share
        the same run_id for proper correlation and audit trail tracking.
        """
        from services.agent_run_logger import AgentRunLogger
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, 'agent_run.log')
            
            logger = AgentRunLogger(log_file_path=log_file)
            
            # Initialize with test run
            request = AgentRunRequest(space_id="test-space", dry_run=True)
            preferences = UserPreferences(voting_strategy=VotingStrategy.BALANCED)
            logger.log_agent_start(request, preferences)
            
            # Verify run_id was set
            assert logger.run_id is not None
            assert logger.run_id.startswith("test-space_")
            
            # Perform multiple operations
            proposals = [Proposal(
                id="prop1",
                title="Test",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0,
                body="Test proposal description"
            )]
            logger.log_proposals_fetched(proposals, 5)
            
            decision = VoteDecision(
                proposal_id="prop1",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test vote execution decision",
                strategy_used=VotingStrategy.BALANCED,
                estimated_gas_cost=0.005
            )
            logger.log_vote_execution(decision, success=True)
            
            # Read log file and verify all messages contain same run_id
            with open(log_file, 'r') as f:
                content = f.read()
            
            run_id_pattern = f"run_id={logger.run_id}"
            log_lines = [line for line in content.split('\n') if 'Agent run' in line or 'Proposals fetched' in line or 'Vote executed' in line]
            
            for line in log_lines:
                assert run_id_pattern in line, f"Log line missing run_id context: {line}"