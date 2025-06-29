<script lang="ts">
  interface Props {
    message?: string;
  }
  
  let { message = "Loading dashboard..." }: Props = $props();
</script>

<div class="flex justify-center items-center py-12">
  <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
  <span class="ml-3 text-secondary-600">{message}</span>
</div>