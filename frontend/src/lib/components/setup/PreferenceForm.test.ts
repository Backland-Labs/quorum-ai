import { describe, it, expect, vi } from 'vitest';
import { fireEvent, waitFor } from '@testing-library/svelte';
import { renderComponent } from '$lib/test-utils';
import PreferenceForm from './PreferenceForm.svelte';

describe('PreferenceForm', () => {
	/**
	 * This test ensures that all necessary form fields are rendered correctly.
	 * It's important because users need to see and interact with all preference options
	 * to properly configure their autonomous voting agent.
	 */
	it('renders all form fields', () => {
		const { getByLabelText, getByRole } = renderComponent(PreferenceForm);
		
		// Check for voting strategy dropdown
		expect(getByLabelText(/voting strategy/i)).toBeInTheDocument();
		
		// Check for confidence threshold input
		expect(getByLabelText(/confidence threshold/i)).toBeInTheDocument();
		
		// Check for max proposals input
		expect(getByLabelText(/maximum proposals per run/i)).toBeInTheDocument();
		
		// Check for blacklisted proposers textarea
		expect(getByLabelText(/blacklisted proposers/i)).toBeInTheDocument();
		
		// Check for whitelisted proposers textarea
		expect(getByLabelText(/whitelisted proposers/i)).toBeInTheDocument();
		
		// Check for submit button
		expect(getByRole('button', { name: /save preferences/i })).toBeInTheDocument();
	});

	/**
	 * This test verifies that the form has correct default values.
	 * It's important to ensure users start with sensible defaults that
	 * provide a balanced voting strategy out of the box.
	 */
	it('has correct default values', () => {
		const { getByLabelText } = renderComponent(PreferenceForm);
		
		// Check default voting strategy is 'balanced'
		const strategySelect = getByLabelText(/voting strategy/i) as HTMLSelectElement;
		expect(strategySelect.value).toBe('balanced');
		
		// Check default confidence threshold is 0.7
		const confidenceInput = getByLabelText(/confidence threshold/i) as HTMLInputElement;
		expect(confidenceInput.value).toBe('0.7');
		
		// Check default max proposals is 5
		const maxProposalsInput = getByLabelText(/maximum proposals per run/i) as HTMLInputElement;
		expect(maxProposalsInput.value).toBe('5');
		
		// Check blacklisted and whitelisted are empty
		const blacklistedTextarea = getByLabelText(/blacklisted proposers/i) as HTMLTextAreaElement;
		expect(blacklistedTextarea.value).toBe('');
		
		const whitelistedTextarea = getByLabelText(/whitelisted proposers/i) as HTMLTextAreaElement;
		expect(whitelistedTextarea.value).toBe('');
	});

	/**
	 * This test ensures form validation works correctly.
	 * It's critical for preventing invalid configurations that could
	 * cause the autonomous agent to behave unexpectedly.
	 */
	it('validates form inputs', async () => {
		const { getByLabelText, getByRole, getByText } = renderComponent(PreferenceForm);
		
		// Test confidence threshold validation (must be between 0 and 1)
		const confidenceInput = getByLabelText(/confidence threshold/i) as HTMLInputElement;
		
		// Set invalid value > 1
		await fireEvent.input(confidenceInput, { target: { value: '1.5' } });
		await fireEvent.blur(confidenceInput);
		expect(getByText(/must be between 0 and 1/i)).toBeInTheDocument();
		
		// Set invalid value < 0
		await fireEvent.input(confidenceInput, { target: { value: '-0.5' } });
		await fireEvent.blur(confidenceInput);
		expect(getByText(/must be between 0 and 1/i)).toBeInTheDocument();
		
		// Test max proposals validation (must be between 1 and 10)
		const maxProposalsInput = getByLabelText(/maximum proposals per run/i) as HTMLInputElement;
		
		// Set invalid value > 10
		await fireEvent.input(maxProposalsInput, { target: { value: '15' } });
		await fireEvent.blur(maxProposalsInput);
		expect(getByText(/must be between 1 and 10/i)).toBeInTheDocument();
		
		// Set invalid value < 1
		await fireEvent.input(maxProposalsInput, { target: { value: '0' } });
		await fireEvent.blur(maxProposalsInput);
		expect(getByText(/must be between 1 and 10/i)).toBeInTheDocument();
	});

	/**
	 * This test verifies that the form submits with correct data.
	 * It's essential to ensure that user preferences are properly
	 * formatted and passed to the parent component for API submission.
	 */
	it('calls onSubmit with form data when submitted', async () => {
		const mockOnSubmit = vi.fn();
		const { getByLabelText, getByRole } = renderComponent(PreferenceForm, {
			props: { onSubmit: mockOnSubmit }
		});
		
		// Fill in the form
		const strategySelect = getByLabelText(/voting strategy/i) as HTMLSelectElement;
		await fireEvent.change(strategySelect, { target: { value: 'aggressive' } });
		
		const confidenceInput = getByLabelText(/confidence threshold/i) as HTMLInputElement;
		await fireEvent.input(confidenceInput, { target: { value: '0.9' } });
		
		const maxProposalsInput = getByLabelText(/maximum proposals per run/i) as HTMLInputElement;
		await fireEvent.input(maxProposalsInput, { target: { value: '8' } });
		
		const blacklistedTextarea = getByLabelText(/blacklisted proposers/i) as HTMLTextAreaElement;
		await fireEvent.input(blacklistedTextarea, { target: { value: '0x123\n0x456' } });
		
		const whitelistedTextarea = getByLabelText(/whitelisted proposers/i) as HTMLTextAreaElement;
		await fireEvent.input(whitelistedTextarea, { target: { value: '0x789\n0xabc' } });
		
		// Submit the form
		const submitButton = getByRole('button', { name: /save preferences/i });
		await fireEvent.click(submitButton);
		
		// Check that onSubmit was called with correct data
		await waitFor(() => {
			expect(mockOnSubmit).toHaveBeenCalledWith({
				voting_strategy: 'aggressive',
				confidence_threshold: 0.9,
				max_proposals_per_run: 8,
				blacklisted_proposers: ['0x123', '0x456'],
				whitelisted_proposers: ['0x789', '0xabc']
			});
		});
	});

	/**
	 * This test ensures the form shows loading state during submission.
	 * It's important for providing user feedback during async operations
	 * and preventing double submissions.
	 */
	it('shows loading state when submitting', async () => {
		const mockOnSubmit = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
		const { getByRole } = renderComponent(PreferenceForm, {
			props: { onSubmit: mockOnSubmit }
		});
		
		const submitButton = getByRole('button', { name: /save preferences/i });
		
		// Button should not be disabled initially
		expect(submitButton).not.toBeDisabled();
		
		// Click submit
		await fireEvent.click(submitButton);
		
		// Button should be disabled and show loading text
		expect(submitButton).toBeDisabled();
		expect(submitButton).toHaveTextContent(/saving/i);
		
		// Wait for submission to complete
		await waitFor(() => {
			expect(submitButton).not.toBeDisabled();
			expect(submitButton).toHaveTextContent(/save preferences/i);
		});
	});

	/**
	 * This test verifies that the form can accept initial values.
	 * It's crucial for the settings page where users need to see
	 * and edit their existing preferences.
	 */
	it('accepts initial values prop', () => {
		const initialValues = {
			voting_strategy: 'conservative' as const,
			confidence_threshold: 0.8,
			max_proposals_per_run: 3,
			blacklisted_proposers: ['0x111', '0x222'],
			whitelisted_proposers: ['0x333']
		};
		
		const { getByLabelText } = renderComponent(PreferenceForm, {
			props: { initialValues }
		});
		
		// Check all fields have initial values
		const strategySelect = getByLabelText(/voting strategy/i) as HTMLSelectElement;
		expect(strategySelect.value).toBe('conservative');
		
		const confidenceInput = getByLabelText(/confidence threshold/i) as HTMLInputElement;
		expect(confidenceInput.value).toBe('0.8');
		
		const maxProposalsInput = getByLabelText(/maximum proposals per run/i) as HTMLInputElement;
		expect(maxProposalsInput.value).toBe('3');
		
		const blacklistedTextarea = getByLabelText(/blacklisted proposers/i) as HTMLTextAreaElement;
		expect(blacklistedTextarea.value).toBe('0x111\n0x222');
		
		const whitelistedTextarea = getByLabelText(/whitelisted proposers/i) as HTMLTextAreaElement;
		expect(whitelistedTextarea.value).toBe('0x333');
	});
});