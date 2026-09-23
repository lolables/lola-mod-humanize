import axios from "axios";
import { authHeader } from "./auth";
import { logRequest } from "./log";
import { validateResponse } from "./validate";

const BASE_URL = "https://api.example.com/v1";
const TIMEOUT = 5000;

class ApiClient {
  constructor(baseUrl = BASE_URL, apiKey = null, timeout = TIMEOUT) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.timeout = timeout;
  }

  async get(path, params = {}) {
    const cfg = {
      method: "GET",
      url: `${this.baseUrl}${path}`,
      params,
      timeout: this.timeout,
      headers: authHeader(this.apiKey),
    };

    logRequest(cfg);

    try {
      const resp = await axios(cfg);
      validateResponse(resp);
      return resp.data;
    } catch (err) {
      throw new Error(`GET ${path} failed: ${err.message}`);
    }
  }

  async post(path, body = {}) {
    const cfg = {
      method: "POST",
      url: `${this.baseUrl}${path}`,
      data: body,
      timeout: this.timeout,
      headers: {
        ...authHeader(this.apiKey),
        "Content-Type": "application/json",
      },
    };

    logRequest(cfg);

    try {
      const resp = await axios(cfg);
      validateResponse(resp);
      return resp.data;
    } catch (err) {
      throw new Error(`POST ${path} failed: ${err.message}`);
    }
  }
}

export { ApiClient };
