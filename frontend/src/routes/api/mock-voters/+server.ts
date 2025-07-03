import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

export const GET: RequestHandler = async ({ params, url }) => {
  const proposalId = url.searchParams.get('proposalId');
  const limit = parseInt(url.searchParams.get('limit') || '10');

  // Simulate delay
  await new Promise(resolve => setTimeout(resolve, 1000));

  // Mock empty state for specific IDs
  if (proposalId === 'empty') {
    return json({
      proposal_id: proposalId,
      voters: []
    });
  }

  // Mock error for specific IDs
  if (proposalId === 'error') {
    return new Response('Internal Server Error', { status: 500 });
  }

  // Generate mock voters
  const mockVoters = Array.from({ length: limit }, (_, i) => ({
    address: `0x${Math.random().toString(16).substring(2, 10)}${Math.random().toString(16).substring(2, 10)}`,
    amount: `${Math.floor(Math.random() * 1000000) * 1e18}`,
    vote_type: ['FOR', 'AGAINST', 'ABSTAIN'][Math.floor(Math.random() * 3)] as 'FOR' | 'AGAINST' | 'ABSTAIN'
  }));

  return json({
    proposal_id: proposalId,
    voters: mockVoters
  });
};
