import createClient from "openapi-fetch";
import type { paths } from "./client";
import { browser } from "$app/environment";

const apiClient = createClient<paths>({
  baseUrl: browser
    ? "http://localhost:8000"  // Browser requests go to host machine
    : "http://backend:8000",   // Server-side requests use Docker service name
});

export default apiClient;
