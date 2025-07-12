"""Activity tracking service for OLAS compliance monitoring."""

import os
import json
from datetime import date
from typing import Dict, Optional, Any
import logfire

from config import settings


class ActivityService:
    """Service for tracking daily activity requirements for OLAS staking compliance."""
    
    def __init__(self):
        """Initialize activity service with persistent state."""
        self.last_activity_date: Optional[date] = None
        self.last_tx_hash: Optional[str] = None
        
        # Setup persistent file path
        if settings.store_path:
            self.persistent_file = os.path.join(settings.store_path, "activity_tracker.json")
        else:
            self.persistent_file = "activity_tracker.json"
            
        self.load_state()
        
        logfire.info(
            "ActivityService initialized",
            persistent_file=self.persistent_file,
            last_activity_date=self.last_activity_date.isoformat() if self.last_activity_date else None,
            daily_activity_needed=self.is_daily_activity_needed()
        )
    
    def load_state(self) -> None:
        """Load activity state from persistent storage."""
        try:
            if os.path.exists(self.persistent_file):
                with open(self.persistent_file, 'r') as f:
                    data = json.load(f)
                    if data.get("last_activity_date"):
                        self.last_activity_date = date.fromisoformat(data["last_activity_date"])
                    self.last_tx_hash = data.get("last_tx_hash")
                    
                logfire.info(
                    "Activity state loaded from file",
                    last_activity_date=self.last_activity_date.isoformat() if self.last_activity_date else None,
                    last_tx_hash=self.last_tx_hash
                )
        except Exception as e:
            logfire.warn(f"Could not load activity state: {e}")
            # Reset to defaults on any error
            self.last_activity_date = None
            self.last_tx_hash = None
    
    def save_state(self) -> None:
        """Save activity state to persistent storage."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.persistent_file), exist_ok=True)
            
            data = {
                "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
                "last_tx_hash": self.last_tx_hash
            }
            
            with open(self.persistent_file, 'w') as f:
                json.dump(data, f)
                
            logfire.info(
                "Activity state saved to file",
                last_activity_date=self.last_activity_date.isoformat() if self.last_activity_date else None,
                last_tx_hash=self.last_tx_hash
            )
        except Exception as e:
            logfire.warn(f"Could not save activity state: {e}")
    
    def is_daily_activity_needed(self) -> bool:
        """Check if we need to create activity for today for OLAS staking.
        
        Returns:
            True if daily activity is required, False if already completed today
        """
        return self.last_activity_date != date.today()
    
    def mark_activity_completed(self, tx_hash: str) -> None:
        """Mark daily activity as completed for OLAS tracking.
        
        Args:
            tx_hash: Transaction hash of the completed activity transaction
        """
        self.last_activity_date = date.today()
        self.last_tx_hash = tx_hash
        self.save_state()
        
        logfire.info(
            "Activity marked as completed",
            tx_hash=tx_hash,
            date=date.today().isoformat()
        )
    
    def get_activity_status(self) -> Dict[str, Any]:
        """Get current activity status for monitoring.
        
        Returns:
            Dict containing activity status information
        """
        return {
            "daily_activity_needed": self.is_daily_activity_needed(),
            "last_activity_date": self.last_activity_date.isoformat() if self.last_activity_date else None,
            "last_tx_hash": self.last_tx_hash,
            "days_since_activity": (date.today() - self.last_activity_date).days if self.last_activity_date else None
        }
    
    def check_olas_compliance(self) -> Dict[str, Any]:
        """Check OLAS staking compliance requirements.
        
        Returns:
            Dict containing compliance status and required actions
        """
        if self.is_daily_activity_needed():
            return {
                "compliant": False,
                "reason": "Daily activity required for OLAS staking",
                "action_required": "safe_transaction",
                "last_activity": self.last_activity_date.isoformat() if self.last_activity_date else None
            }
        else:
            return {
                "compliant": True,
                "reason": "Daily activity completed",
                "action_required": None,
                "last_activity": self.last_activity_date.isoformat() if self.last_activity_date else None
            }
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get comprehensive compliance summary for reporting.
        
        Returns:
            Dict containing complete activity and compliance information
        """
        return {
            "activity_status": self.get_activity_status(),
            "olas_compliance": self.check_olas_compliance()
        }
    
    async def ensure_daily_compliance(self, safe_service) -> Dict[str, Any]:
        """Ensure daily OLAS compliance by triggering Safe transaction if needed.
        
        Args:
            safe_service: SafeService instance for creating transactions
            
        Returns:
            Dict containing compliance action results
        """
        with logfire.span("activity_service.ensure_daily_compliance"):
            compliance_status = self.check_olas_compliance()
            
            if not compliance_status["compliant"]:
                logfire.info("Daily OLAS activity needed - requesting Safe transaction")
                
                # Request Safe transaction for activity
                transaction_result = await safe_service.perform_activity_transaction()
                
                if transaction_result["success"]:
                    # Mark activity as completed
                    self.mark_activity_completed(transaction_result["tx_hash"])
                    
                    return {
                        "action_taken": "safe_transaction",
                        "success": True,
                        "transaction_result": transaction_result,
                        "compliance_status": self.check_olas_compliance()  # Updated status
                    }
                else:
                    return {
                        "action_taken": "safe_transaction",
                        "success": False,
                        "error": transaction_result.get("error"),
                        "compliance_status": compliance_status
                    }
            else:
                logfire.info("Daily OLAS activity already completed")
                return {
                    "action_taken": "none",
                    "success": True,
                    "message": "Daily activity already completed",
                    "compliance_status": compliance_status
                }