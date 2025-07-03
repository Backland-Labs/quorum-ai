export type TabType = 'overview' | 'proposals' | 'activity';

export interface Tab {
  id: TabType;
  label: string;
  content?: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  chain_ids?: string[];
  token_ids?: string[];
  governor_ids?: string[];
  metadata?: any;
  creator?: any;
  has_active_proposals: boolean;
  proposals_count: number;
  delegates_count: number;
  delegates_votes_count: string;
  token_owners_count: number;
  endorsement_service?: any;
}

export interface OrganizationWithProposals {
  organization: Organization;
  proposals: Proposal[];
}

export interface Proposal {
  proposal_id: string;
  title: string;
  summary: string;
  key_points: string[];
  risk_level: string;
  recommendation: string;
  confidence_score: number;
}

export interface ProposalDetails extends Proposal {
  id: string;
  description: string;
  state: string;
  created_at: string;
  start_block: number;
  end_block: number;
  votes_for: string;
  votes_against: string;
  votes_abstain: string;
  dao_id: string;
  dao_name: string;
  url?: string;
}

export interface DashboardState {
  activeTab: TabType;
  selectedOrganization: Organization | null;
  organizations: OrganizationWithProposals[];
  loading: boolean;
  error: string | null;
}

export interface TabNavigationProps {
  tabs: Tab[];
  activeTab: TabType;
  onTabChange: (tabId: TabType) => void;
}

export interface OrganizationDropdownProps {
  organizations: Organization[];
  selectedOrganization: Organization | null;
  onOrganizationChange: (organization: Organization) => void;
  loading?: boolean;
}
