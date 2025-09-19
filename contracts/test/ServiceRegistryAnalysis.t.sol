// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";

// Minimal interface to explore Service Registry
interface IServiceRegistryExplorer {
    function totalSupply() external view returns (uint256);
    function exists(uint256 serviceId) external view returns (bool);
    function ownerOf(uint256 serviceId) external view returns (address);
    function tokenByIndex(uint256 index) external view returns (uint256);
    function tokenOfOwnerByIndex(address owner, uint256 index) external view returns (uint256);
    function balanceOf(address owner) external view returns (uint256);
}

// Alternative service registry interface - might be older version
interface IServiceRegistryAlt {
    function getUnitHash(uint256 serviceId) external view returns (bytes32);
    function serviceExists(uint256 serviceId) external view returns (bool);
}

/**
 * @title ServiceRegistryAnalysis
 * @dev Analyze the Service Registry to understand its structure and find suitable services
 */
contract ServiceRegistryAnalysisTest is Test {
    IServiceRegistryExplorer public serviceRegistry = IServiceRegistryExplorer(0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE);
    
    function setUp() public {
        vm.createFork("https://mainnet.base.org");
        console.log("=== SERVICE REGISTRY ANALYSIS ===");
        console.log("Registry at:", address(serviceRegistry));
    }

    function test_01_BasicRegistryInfo() public view {
        console.log("=== Test 1: Basic Registry Information ===");
        
        uint256 totalServices = serviceRegistry.totalSupply();
        console.log("Total services:", totalServices);
        
        // Check if this is an ERC721-like registry
        for (uint256 i = 0; i < 10 && i < totalServices; i++) {
            try serviceRegistry.tokenByIndex(i) returns (uint256 tokenId) {
                console.log("Token at index", i, "has ID:", tokenId);
                
                try serviceRegistry.ownerOf(tokenId) returns (address owner) {
                    console.log("  Owner:", owner);
                } catch {
                    console.log("  Could not get owner");
                }
            } catch {
                console.log("Token by index", i, "failed");
            }
        }
    }

    function test_02_DirectServiceAccess() public view {
        console.log("=== Test 2: Direct Service Access ===");
        
        // Try to access services directly by ID
        for (uint256 i = 1; i <= 20; i++) {
            bool exists = serviceRegistry.exists(i);
            console.log("Service", i, "exists:", exists);
            
            if (exists) {
                try serviceRegistry.ownerOf(i) returns (address owner) {
                    console.log("  Owner:", owner);
                    
                    // Check if owner has multiple services
                    try serviceRegistry.balanceOf(owner) returns (uint256 balance) {
                        console.log("  Owner has", balance, "services");
                    } catch {
                        console.log("  Could not get owner balance");
                    }
                } catch {
                    console.log("  Could not get owner for service", i);
                }
            }
        }
    }

    function test_03_AlternativeInterface() public view {
        console.log("=== Test 3: Alternative Interface ===");
        
        IServiceRegistryAlt altRegistry = IServiceRegistryAlt(address(serviceRegistry));
        
        for (uint256 i = 1; i <= 10; i++) {
            try altRegistry.serviceExists(i) returns (bool exists) {
                console.log("Service", i, "exists (alt):", exists);
                
                if (exists) {
                    try altRegistry.getUnitHash(i) returns (bytes32 hash) {
                        console.log("  Unit hash:", uint256(hash));
                    } catch {
                        console.log("  Could not get unit hash");
                    }
                }
            } catch {
                console.log("Service", i, "alt interface failed");
            }
        }
    }
    
    function test_04_FindActiveServices() public view {
        console.log("=== Test 4: Find Active Services ===");
        
        uint256 totalServices = serviceRegistry.totalSupply();
        console.log("Scanning", totalServices, "services for active ones...");
        
        uint256 foundServices = 0;
        for (uint256 i = 1; i <= totalServices && foundServices < 10; i++) {
            if (serviceRegistry.exists(i)) {
                try serviceRegistry.ownerOf(i) returns (address owner) {
                    if (owner != address(0)) {
                        console.log("Active service", i, "owned by:", owner);
                        foundServices++;
                        
                        // This service exists and has an owner - it might be suitable for staking
                        console.log("  -> Potential candidate for staking test");
                    }
                } catch {
                    // Skip services we can't get owner for
                }
            }
        }
        
        console.log("Found", foundServices, "potentially active services");
    }
}