<script lang="ts">
  import '../app.css';
  interface Props {
    children?: import('svelte').Snippet;
  }

  let { children }: Props = $props();
</script>

<div class="min-h-screen bg-secondary-50">
  <!-- Navigation Header -->
  <header class="bg-white shadow-sm border-b border-secondary-200">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex justify-between items-center h-16">
        <div class="flex items-center">
          <h1 class="text-xl font-bold text-primary-600">Quorum AI</h1>
        </div>
        <nav class="flex space-x-8">
          <a href="/" class="text-secondary-600 hover:text-primary-600 font-medium transition-colors duration-200">
            Organizations
          </a>
        </nav>
      </div>
    </div>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    {@render children?.()}
  </main>
</div>