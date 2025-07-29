import createClient from "openapi-fetch";
import type { paths } from "./client";
import { browser } from "$app/environment";

// API configuration constants
const API_PORT = "8716";
const API_HOST_BROWSER = "localhost";
const API_HOST_SERVER = "backend";

const apiClient = createClient<paths>({
  baseUrl: browser
    ? `http://${API_HOST_BROWSER}:${API_PORT}`  // Browser requests go to host machine
    : `http://${API_HOST_SERVER}:${API_PORT}`,   // Server-side requests use Docker service name
});

export { apiClient };
export default apiClient;
