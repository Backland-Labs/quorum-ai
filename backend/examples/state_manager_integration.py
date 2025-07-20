"""Example integration of StateManager with existing services.

This example demonstrates how the StateManager can be used to persist
various types of application state in the Quorum AI agent.
"""

import asyncio
import os
from pathlib import Path

# Set up test environment
os.environ["STORE_PATH"] = str(Path.home() / ".quorum_ai_test")

from services.state_manager import StateManager, StateSchema, StateVersion
from services.user_preferences_service import UserPreferencesService


async def example_user_preferences_integration():
    """Example: Using StateManager for user preferences persistence."""
    # Initialize services
    state_manager = StateManager()
    preferences_service = UserPreferencesService()
    
    # Define schema for user preferences
    preferences_schema = StateSchema(
        required_fields=["voting_strategy", "risk_threshold"],
        field_types={
            "voting_strategy": str,
            "risk_threshold": float,
            "auto_vote_enabled": bool,
            "notification_settings": dict,
        },
        validators={
            "risk_threshold": lambda x: 0.0 <= x <= 1.0,
            "voting_strategy": lambda x: x in ["balanced", "conservative", "aggressive"],
        },
    )
    
    # Save user preferences
    preferences_data = {
        "voting_strategy": "balanced",
        "risk_threshold": 0.7,
        "auto_vote_enabled": True,
        "notification_settings": {
            "email": True,
            "in_app": True,
            "frequency": "daily",
        },
    }
    
    await state_manager.save_state(
        "user_preferences",
        preferences_data,
        schema=preferences_schema,
        version=StateVersion(1, 0, 0),
    )
    
    print("✅ User preferences saved with schema validation")
    
    # Load and validate preferences
    loaded_prefs = await state_manager.load_state(
        "user_preferences", schema=preferences_schema
    )
    print(f"📋 Loaded preferences: {loaded_prefs}")


async def example_voting_history_persistence():
    """Example: Persisting voting history with automatic backups."""
    state_manager = StateManager()
    
    # Initial voting history
    voting_history = {
        "total_votes": 0,
        "votes_by_space": {},
        "recent_votes": [],
    }
    
    # Simulate multiple voting sessions
    for i in range(5):
        # Add a vote
        vote = {
            "proposal_id": f"0x{i:03d}",
            "space": "example.eth",
            "choice": "FOR",
            "timestamp": f"2024-01-{i+1:02d}T12:00:00Z",
        }
        
        voting_history["total_votes"] += 1
        voting_history["votes_by_space"].setdefault("example.eth", 0)
        voting_history["votes_by_space"]["example.eth"] += 1
        voting_history["recent_votes"].append(vote)
        
        # Keep only last 100 votes
        if len(voting_history["recent_votes"]) > 100:
            voting_history["recent_votes"] = voting_history["recent_votes"][-100:]
        
        # Save state (creates automatic backups)
        await state_manager.save_state("voting_history", voting_history)
        print(f"💾 Saved voting history (vote #{i+1})")
    
    # List available backups
    backups = await state_manager.list_backups("voting_history")
    print(f"📁 Available backups: {len(backups)}")
    
    # Simulate corruption and recovery
    if backups:
        print("🔄 Simulating recovery from backup...")
        recovered = await state_manager.restore_from_backup(
            "voting_history", backups[0]
        )
        print(f"✅ Recovered {recovered['total_votes']} votes from backup")


async def example_agent_state_versioning():
    """Example: Managing agent state with versioning and migrations."""
    state_manager = StateManager()
    
    # Version 1.0.0 - Initial agent state
    agent_state_v1 = {
        "agent_id": "quorum-001",
        "status": "active",
        "config": {
            "poll_interval": 300,
            "max_concurrent_votes": 5,
        },
        "metrics": {
            "uptime_hours": 0,
            "proposals_analyzed": 0,
        },
    }
    
    await state_manager.save_state(
        "agent_state",
        agent_state_v1,
        version=StateVersion(1, 0, 0),
    )
    print("📌 Saved agent state v1.0.0")
    
    # Define migration from v1 to v2
    # v2 adds risk_assessment_enabled and splits metrics
    def migrate_v1_to_v2(data):
        # Add new config field
        data["config"]["risk_assessment_enabled"] = True
        
        # Split metrics into performance and reliability
        old_metrics = data.pop("metrics", {})
        data["performance_metrics"] = {
            "proposals_analyzed": old_metrics.get("proposals_analyzed", 0),
            "average_analysis_time": 0.0,
        }
        data["reliability_metrics"] = {
            "uptime_hours": old_metrics.get("uptime_hours", 0),
            "error_rate": 0.0,
        }
        
        return data
    
    # Register migration
    state_manager.register_migration(
        StateVersion(1, 0, 0),
        StateVersion(2, 0, 0),
        migrate_v1_to_v2,
    )
    
    # Load with automatic migration to v2
    agent_state_v2 = await state_manager.load_state(
        "agent_state",
        target_version=StateVersion(2, 0, 0),
    )
    print("📈 Migrated agent state to v2.0.0")
    print(f"   - New config: {agent_state_v2['config']}")
    print(f"   - Performance metrics: {agent_state_v2['performance_metrics']}")
    print(f"   - Reliability metrics: {agent_state_v2['reliability_metrics']}")


async def example_sensitive_data_handling():
    """Example: Handling sensitive data with proper permissions."""
    state_manager = StateManager()
    
    # Save API keys and credentials with restricted permissions
    sensitive_data = {
        "openrouter_api_key": "sk-or-v1-example",
        "snapshot_api_key": "snapshot-key-example",
        "wallet_config": {
            "address": "0x1234...5678",
            "encrypted_key": "encrypted-private-key-data",
        },
    }
    
    await state_manager.save_state(
        "credentials",
        sensitive_data,
        sensitive=True,  # Sets 0o600 permissions
    )
    print("🔒 Saved sensitive credentials with restricted permissions")
    
    # Load sensitive data (validates permissions)
    try:
        loaded_creds = await state_manager.load_state(
            "credentials",
            sensitive=True,
        )
        print("✅ Loaded credentials securely")
    except Exception as e:
        print(f"❌ Failed to load credentials: {e}")


async def main():
    """Run all examples."""
    print("🚀 State Manager Integration Examples\n")
    
    print("1️⃣ User Preferences Integration")
    print("-" * 40)
    await example_user_preferences_integration()
    print()
    
    print("2️⃣ Voting History Persistence")
    print("-" * 40)
    await example_voting_history_persistence()
    print()
    
    print("3️⃣ Agent State Versioning")
    print("-" * 40)
    await example_agent_state_versioning()
    print()
    
    print("4️⃣ Sensitive Data Handling")
    print("-" * 40)
    await example_sensitive_data_handling()
    print()
    
    # Cleanup
    state_manager = StateManager()
    await state_manager.cleanup()
    print("🧹 Cleaned up resources")


if __name__ == "__main__":
    asyncio.run(main())