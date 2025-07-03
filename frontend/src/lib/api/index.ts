import createClient from "openapi-fetch";
import type { paths } from "./client";

const apiClient = createClient<paths>({
  baseUrl: "http://127.0.0.1:8000",
});

export default apiClient;
