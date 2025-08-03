import type { OrganizationWithProposals } from '$lib/types/dashboard.js';

/**
 * Extracts error message from API error response
 * @param apiError - The API error object
 * @returns Formatted error message string
 */
export function extractApiErrorMessage(apiError: unknown): string {
  console.assert(apiError !== null, 'API error should not be null');
  console.assert(apiError !== undefined, 'API error should not be undefined');

  if (apiError && typeof apiError === 'object' && 'message' in apiError) {
    return String((apiError as any).message);
  }
  return "Failed to load organizations";
}

/**
 * Check if an API response has an error
 * @param response - The API response from openapi-fetch
 * @returns True if the response has an error
 */
export function hasApiError(response: any): boolean {
  return response && response.error !== undefined;
}

/**
 * Get the status code from an API error response
 * @param response - The API response from openapi-fetch
 * @returns The status code or 500 as default
 */
export function getApiErrorStatus(response: any): number {
  if (response && response.response && response.response.status) {
    return response.response.status;
  }
  return 500;
}

/**
 * Selects the default organization from API response
 * @param organizations - Array of organizations with proposals
 * @returns First organization or null if empty
 */
export function selectDefaultOrganization(
  organizations: OrganizationWithProposals[]
): OrganizationWithProposals['organization'] | null {
  console.assert(Array.isArray(organizations), 'Organizations must be an array');
  console.assert(organizations !== null, 'Organizations cannot be null');

  if (organizations.length > 0) {
    return organizations[0].organization;
  }
  return null;
}
