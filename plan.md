# Olas Service Template Configuration Plan

## Overview

**Linear Issue**: `BAC-188` - Create Olas service template JSON configuration

**Objective**: To create a complete and valid `service-template.json` file for the Quorum AI agent. This file is a critical requirement for deploying the agent as a service on the Olas Pearl platform, defining its on-chain configuration, funding requirements, and necessary environment variables.

This plan follows a Test-Driven Development (TDD) approach. For each task, the engineer will first write tests that validate the acceptance criteria, then implement the feature to make the tests pass, and finally refactor for clarity and correctness.

## Prioritized Features

### P0: Core Template Structure & Validation
- **Task 1**: Create the `service-template.json` file with the basic top-level structure.
- **Task 2**: Implement the `configurations` block with a focus on Gnosis chain and funding requirements.
- **Task 3**: Implement the `env_variables` block, correctly categorizing each variable.
- **Task 4**: Perform a final validation of the complete JSON structure against the Olas schema.

---

## Implementation Tasks

### Task 1: Create Service Template File and Basic Structure

**Acceptance Criteria:**
- A valid JSON file named `service-template.json` exists in the project's root directory.
- The file contains the correct top-level keys (`name`, `hash`, `description`, `image`, `service_version`, `home_chain`) with their specified values.
- The `hash` field is set to a placeholder value `<service_hash>`.

**TDD Cycle:**
1.  **Test (Red):**
    - Write a test `test_file_exists_and_is_valid_json()` that:
        - Asserts `service-template.json` exists.
        - Asserts the file content can be parsed as valid JSON.
    - Write a test `test_has_correct_top_level_keys()` that:
        - Loads the JSON file.
        - Asserts the presence and correct values for `name`, `description`, `service_version`, and `home_chain`.
        - Asserts the `hash` key exists and has a placeholder value.
        - Asserts the `image` key exists and is an empty string.

2.  **Implement (Green):**
    - Create a new file named `service-template.json` in the root directory.
    - Populate the file with the following content:
      ```json
      {
        "name": "quorum_agent",
        "hash": "<service_hash>",
        "description": "Autonomous DAO governance voting agent with AI-powered proposal analysis",
        "image": "",
        "service_version": "v0.1.0",
        "home_chain": "gnosis"
      }
      ```

3.  **Refactor:**
    - Ensure JSON is well-formatted and readable.

---

### Task 2: Implement Chain Configuration and Funding Requirements

**Acceptance Criteria:**
- The `service-template.json` file includes a `configurations` block.
- The `gnosis` chain configuration is present with the correct `agent_id` (placeholder), `nft`, `threshold`, `use_staking`, `staking_program_id` (placeholder), and `use_mech_marketplace` values.
- The `fund_requirements` are correctly defined for the native token (`0x0...0`) on Gnosis, with wei values corresponding to 0.005 xDAI for the agent and 0.01 xDAI for the safe.

**TDD Cycle:**
1.  **Test (Red):**
    - Write a test `test_gnosis_configuration_exists()` that:
        - Loads the JSON file.
        - Asserts the `configurations.gnosis` object exists.
        - Asserts the presence and correct values for `nft`, `threshold`, `use_staking`, and `use_mech_marketplace`.
        - Asserts the presence of placeholder values for `agent_id` and `staking_program_id`.
    - Write a test `test_funding_requirements_are_correct()` that:
        - Asserts `configurations.gnosis.fund_requirements` exists.
        - Asserts the native token key (`0x000...`) is present.
        - Asserts `agent` funding is exactly `5000000000000000`.
        - Asserts `safe` funding is exactly `10000000000000000`.

2.  **Implement (Green):**
    - Add the `configurations` block to `service-template.json` with the specified Gnosis chain data and funding requirements.

3.  **Refactor:**
    - Add comments in the test file to clarify the xDAI to wei conversion for funding amounts.

---

### Task 3: Implement Environment Variable Specifications

**Acceptance Criteria:**
- The `service-template.json` file includes an `env_variables` block.
- All specified environment variables are present with the correct `name`, `description`, `value`, and `provision_type`.
- Variables are correctly categorized as `computed`, `user`, or `fixed`.

**TDD Cycle:**
1.  **Test (Red):**
    - Write a test `test_env_variables_structure_is_correct()` that:
        - Loads the JSON file.
        - Asserts the `env_variables` object exists and contains all 9 required keys.
    - Write a test `test_env_variable_provision_types()` that:
        - Iterates through the `env_variables` object.
        - Asserts that each variable has the correct `provision_type` as specified in the requirements.
    - Write a test `test_env_variable_default_values()` that:
        - Asserts that `user` and `fixed` variables have the correct default `value`.
        - Asserts that `computed` variables have an empty string `value`.

2.  **Implement (Green):**
    - Add the `env_variables` block to `service-template.json` and populate it with all 9 specified environment variable configurations.

3.  **Refactor:**
    - Organize the variables in the JSON file by `provision_type` to improve readability.

---

### Task 4: Final Validation and Review

**Acceptance Criteria:**
- The final `service-template.json` is a well-formed JSON document.
- The structure and values match the technical requirements precisely.
- The file is placed in the project's root directory.

**TDD Cycle (Manual/Verification):**
1.  **Test (Red):**
    - Create a validation script or use an online tool to validate the generated `service-template.json` against the Olas service template schema (if available from Olas docs).
    - The script should fail initially if the file is incomplete or malformed.

2.  **Implement (Green):**
    - Run the validation script/tool against the completed `service-template.json`.
    - Fix any discrepancies in structure, data types, or required fields until validation passes.

3.  **Refactor:**
    - Add a section to the project's `README.md` explaining the purpose of `service-template.json` and which placeholder values (`<service_hash>`, `<agent_id>`, `<staking_program_id>`) need to be replaced during deployment.

---

## Success Criteria

- [x] A `service-template.json` file is created in the project root. (Implemented: 2025-01-27)
- [x] The file contains a valid JSON object conforming to the specified structure. (Implemented: 2025-01-27)
- [x] Gnosis chain funding requirements are correctly set to 0.005 xDAI (agent) and 0.01 xDAI (safe) in wei. (Implemented: 2025-01-27)
- [x] All required environment variables are defined and correctly categorized by `provision_type`. (Implemented: 2025-01-27)
- [x] Placeholder values for `hash`, `agent_id`, and `staking_program_id` are present. (Implemented: 2025-01-27)
- [x] The plan is fully implemented, and all associated tests are passing. (Implemented: 2025-01-27)

## Implementation Status: COMPLETED

All tasks have been successfully implemented following TDD methodology:
- Task 1: ✅ Created service template file with basic structure
- Task 2: ✅ Implemented chain configuration and funding requirements  
- Task 3: ✅ Implemented environment variable specifications
- Task 4: ✅ Final validation and review completed

Additional deliverables:
- Created comprehensive test suite with 16 passing tests
- Created SERVICE_TEMPLATE_README.md with deployment instructions
- Used correct Olas Pearl format with chain ID "100" instead of "gnosis"
- Used proper IPFS hash format and Docker image naming convention
