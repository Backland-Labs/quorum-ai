<script lang="ts">
  import type { TabNavigationProps } from '../types/dashboard.js';
  
  interface Props extends TabNavigationProps {}
  
  let { tabs, activeTab, onTabChange }: Props = $props();

  const handleTabClick = (tabId: typeof activeTab) => {
    onTabChange(tabId);
  };

  const handleKeydown = (event: KeyboardEvent, tabId: typeof activeTab) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      handleTabClick(tabId);
    }
  };
</script>

<div class="flex space-x-8 border-b border-secondary-200" role="tablist">
  {#each tabs as tab (tab.id)}
    <button
      type="button"
      class="py-2 px-1 border-b-2 font-medium text-sm transition-colors duration-200
             {activeTab === tab.id 
               ? 'border-primary-500 text-primary-600' 
               : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300'
             }
             focus:outline-none focus:text-primary-600 focus:border-primary-500"
      onclick={() => handleTabClick(tab.id)}
      onkeydown={(e) => handleKeydown(e, tab.id)}
      role="tab"
      aria-selected={activeTab === tab.id}
      aria-controls="tab-panel-{tab.id}"
      tabindex={activeTab === tab.id ? 0 : -1}
    >
      {tab.label}
    </button>
  {/each}
</div>