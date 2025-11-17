import devtoolsJson from 'vite-plugin-devtools-json';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit(), devtoolsJson()],
	server: {
		proxy: {
			'/healthcheck': 'http://localhost:8716',
			'/staking': 'http://localhost:8716',
			'/agent-run': 'http://localhost:8716',
			'/config': 'http://localhost:8716',
			'/proposals': 'http://localhost:8716',
			'/user-preferences': 'http://localhost:8716',
			'/verify': 'http://localhost:8716'
		}
	}
});
