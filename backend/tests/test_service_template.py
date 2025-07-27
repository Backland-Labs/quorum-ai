"""Test suite for Olas service template configuration.

This test suite ensures that the service-template.json file:
1. Contains all required fields with correct structure
2. Has proper chain configuration and funding requirements
3. Includes all necessary environment variables
4. Is valid JSON and follows the Olas Pearl format
"""

import json
import pytest
from pathlib import Path


class TestServiceTemplate:
    """Test cases for service-template.json validation."""
    
    def test_service_template_file_exists(self):
        """Test that service-template.json exists in the project root.
        
        Why: The service template is required for deploying on Olas Pearl.
        What: Verifies the file exists at the expected location.
        """
        template_path = Path("service-template.json")
        assert template_path.exists(), "service-template.json must exist in project root"
    
    def test_service_template_is_valid_json(self):
        """Test that service-template.json contains valid JSON.
        
        Why: Invalid JSON will cause deployment failures.
        What: Parses the file to ensure JSON validity.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)  # Will raise if invalid JSON
        assert isinstance(template, dict), "Template must be a JSON object"
    
    def test_required_top_level_fields(self):
        """Test that all required top-level fields are present.
        
        Why: Olas Pearl requires specific fields for service registration.
        What: Checks for name, hash, description, image, service_version, and home_chain.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        required_fields = ["name", "hash", "description", "image", "service_version", "home_chain"]
        for field in required_fields:
            assert field in template, f"Missing required field: {field}"
    
    def test_service_metadata_values(self):
        """Test that service metadata has correct values.
        
        Why: These values identify and describe the service on Olas Pearl.
        What: Validates specific field values match requirements.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        assert template["name"] == "Quorum AI Agent", "Service name must be 'Quorum AI Agent'"
        assert template["description"] == "Autonomous DAO voting agent with AI-powered decision making", \
            "Description must match specification"
        assert template["service_version"] == "0.1.0", "Service version must be 0.1.0"
        assert template["home_chain"] == "100", "Home chain must be 100 (Gnosis)"
    
    def test_hash_format(self):
        """Test that hash field follows correct format.
        
        Why: Hash must match the actual agent package hash for verification.
        What: Validates hash is a non-empty string with expected length.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        hash_value = template.get("hash", "")
        assert isinstance(hash_value, str), "Hash must be a string"
        assert len(hash_value) == 46, "Hash must be 46 characters (IPFS CIDv0 format)"
        assert hash_value.startswith("Qm"), "Hash must be IPFS CIDv0 (starts with Qm)"
    
    def test_image_format(self):
        """Test that image field has correct Docker image format.
        
        Why: Image must be pullable from a registry for deployment.
        What: Validates Docker image naming convention.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        image = template.get("image", "")
        assert isinstance(image, str), "Image must be a string"
        assert "/" in image, "Image must include registry/namespace"
        assert ":" in image, "Image must include tag"
        assert "oar-quorum-ai" in image, "Image name must contain 'oar-quorum-ai'"
    
    def test_configurations_structure(self):
        """Test that configurations field has correct structure.
        
        Why: Chain-specific configurations define deployment parameters.
        What: Validates configurations is an object with chain IDs as keys.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        assert "configurations" in template, "Missing configurations field"
        configs = template["configurations"]
        assert isinstance(configs, dict), "Configurations must be an object"
        assert "100" in configs, "Must have configuration for chain 100 (Gnosis)"
    
    def test_gnosis_chain_configuration(self):
        """Test Gnosis chain configuration details.
        
        Why: Gnosis is the target deployment chain with specific requirements.
        What: Validates funding requirements and staking parameters.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        gnosis_config = template["configurations"]["100"]
        
        # Check required fields
        required_fields = ["staking_program", "agent_fund_requirement", "fund_requirement"]
        for field in required_fields:
            assert field in gnosis_config, f"Missing field in Gnosis config: {field}"
        
        # Validate values
        assert gnosis_config["staking_program"] == "pearl_alpha", \
            "Staking program must be 'pearl_alpha'"
        assert gnosis_config["agent_fund_requirement"] == "5000000000000000", \
            "Agent fund requirement must be 0.005 xDAI (5000000000000000 wei)"
        assert gnosis_config["fund_requirement"] == "10000000000000000", \
            "Total fund requirement must be 0.01 xDAI (10000000000000000 wei)"
    
    def test_environment_variables_structure(self):
        """Test that env_variables field has correct structure.
        
        Why: Environment variables configure the agent's runtime behavior.
        What: Validates env_variables is an array with proper schema.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        assert "env_variables" in template, "Missing env_variables field"
        env_vars = template["env_variables"]
        assert isinstance(env_vars, list), "env_variables must be an array"
        assert len(env_vars) > 0, "env_variables must not be empty"
    
    def test_environment_variable_schema(self):
        """Test that each environment variable has correct schema.
        
        Why: Each variable must follow Olas Pearl's expected format.
        What: Validates name, description, and provision_type fields.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        for i, env_var in enumerate(template["env_variables"]):
            assert isinstance(env_var, dict), f"env_variables[{i}] must be an object"
            
            # Check required fields
            required_fields = ["name", "description", "provision_type"]
            for field in required_fields:
                assert field in env_var, f"env_variables[{i}] missing field: {field}"
            
            # Validate provision_type
            valid_types = ["fixed", "user", "computed"]
            assert env_var["provision_type"] in valid_types, \
                f"env_variables[{i}] has invalid provision_type: {env_var['provision_type']}"
            
            # If fixed type, must have value
            if env_var["provision_type"] == "fixed":
                assert "value" in env_var, f"Fixed env_variables[{i}] must have value field"
    
    def test_required_environment_variables(self):
        """Test that all required environment variables are defined.
        
        Why: The agent needs specific variables to function correctly.
        What: Validates presence of all 9 required variables from the plan.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        env_names = {var["name"] for var in template["env_variables"]}
        
        # Required variables from the plan
        required_vars = {
            # Computed variables
            "ETHEREUM_LEDGER_RPC",
            "GNOSIS_LEDGER_RPC",
            "AGENT_ADDRESS",
            "SAFE_ADDRESS",
            
            # User variables
            "OPENROUTER_API_KEY",
            
            # Fixed variables
            "STORE_PATH",
            "HEALTH_CHECK_PORT",
            "PORT",
            "DEBUG"
        }
        
        missing_vars = required_vars - env_names
        assert not missing_vars, f"Missing required environment variables: {missing_vars}"
    
    def test_computed_environment_variables(self):
        """Test computed environment variables configuration.
        
        Why: Computed variables are populated by Olas Pearl at runtime.
        What: Validates computed variables have correct provision_type.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        computed_vars = {
            "ETHEREUM_LEDGER_RPC": "RPC endpoint for Ethereum network",
            "GNOSIS_LEDGER_RPC": "RPC endpoint for Gnosis network", 
            "AGENT_ADDRESS": "Agent's blockchain address",
            "SAFE_ADDRESS": "Safe wallet address for agent"
        }
        
        for var in template["env_variables"]:
            if var["name"] in computed_vars:
                assert var["provision_type"] == "computed", \
                    f"{var['name']} must have provision_type 'computed'"
                assert var["description"] == computed_vars[var["name"]], \
                    f"{var['name']} has incorrect description"
    
    def test_user_environment_variables(self):
        """Test user-provided environment variables configuration.
        
        Why: User must provide API keys for the agent to function.
        What: Validates user variables have correct provision_type.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        user_vars = {
            "OPENROUTER_API_KEY": "API key for OpenRouter AI service"
        }
        
        for var in template["env_variables"]:
            if var["name"] in user_vars:
                assert var["provision_type"] == "user", \
                    f"{var['name']} must have provision_type 'user'"
                assert var["description"] == user_vars[var["name"]], \
                    f"{var['name']} has incorrect description"
    
    def test_fixed_environment_variables(self):
        """Test fixed environment variables configuration.
        
        Why: Fixed variables configure agent behavior consistently.
        What: Validates fixed variables have correct values and provision_type.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        fixed_vars = {
            "STORE_PATH": ("/app/data", "Path for persistent data storage"),
            "HEALTH_CHECK_PORT": ("8716", "Port for health check endpoint"),
            "PORT": ("8716", "Main application port"),
            "DEBUG": ("false", "Debug mode flag")
        }
        
        for var in template["env_variables"]:
            if var["name"] in fixed_vars:
                expected_value, expected_desc = fixed_vars[var["name"]]
                assert var["provision_type"] == "fixed", \
                    f"{var['name']} must have provision_type 'fixed'"
                assert var["value"] == expected_value, \
                    f"{var['name']} has incorrect value"
                assert var["description"] == expected_desc, \
                    f"{var['name']} has incorrect description"
    
    def test_no_duplicate_environment_variables(self):
        """Test that there are no duplicate environment variable names.
        
        Why: Duplicate variables would cause configuration conflicts.
        What: Ensures all variable names are unique.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        env_names = [var["name"] for var in template["env_variables"]]
        assert len(env_names) == len(set(env_names)), \
            "Environment variable names must be unique"
    
    def test_environment_variables_order(self):
        """Test that environment variables are ordered by provision type.
        
        Why: Consistent ordering improves readability and maintenance.
        What: Validates variables are grouped: computed, user, then fixed.
        """
        with open("service-template.json", "r") as f:
            template = json.load(f)
        
        # Extract provision types in order
        provision_types = [var["provision_type"] for var in template["env_variables"]]
        
        # Check grouping
        computed_end = max([i for i, t in enumerate(provision_types) if t == "computed"], default=-1)
        user_start = min([i for i, t in enumerate(provision_types) if t == "user"], default=len(provision_types))
        user_end = max([i for i, t in enumerate(provision_types) if t == "user"], default=-1)
        fixed_start = min([i for i, t in enumerate(provision_types) if t == "fixed"], default=len(provision_types))
        
        # Validate ordering
        if computed_end >= 0 and user_start < len(provision_types):
            assert computed_end < user_start, "Computed variables must come before user variables"
        if user_end >= 0 and fixed_start < len(provision_types):
            assert user_end < fixed_start, "User variables must come before fixed variables"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])