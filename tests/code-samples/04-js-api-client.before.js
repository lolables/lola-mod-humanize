import axios from "axios";
import { formatErrorMessage } from "./errorFormatter";
import { getAuthorizationHeader } from "./authorizationHelper";
import { logApiRequest } from "./requestLogger";
import { validateApiResponse } from "./responseValidator";

// --- Configuration ---

const DEFAULT_REQUEST_TIMEOUT_MILLISECONDS = 5000;
const DEFAULT_API_BASE_URL = "https://api.example.com/v1";

// --- Factory ---

/**
 * Creates and returns a fully configured ApiClient instance.
 *
 * @param {Object} clientConfigurationOptions - The configuration options for the client.
 * @param {string} clientConfigurationOptions.baseUrl - The base URL of the API.
 * @param {string} clientConfigurationOptions.apiKey - The API key for authentication.
 * @param {number} clientConfigurationOptions.timeoutMilliseconds - The request timeout in milliseconds.
 * @returns {ApiClient} A configured ApiClient instance.
 */
function createApiClientInstance(clientConfigurationOptions = {}) {
  const resolvedBaseUrl =
    clientConfigurationOptions.baseUrl || DEFAULT_API_BASE_URL;
  const resolvedApiKey = clientConfigurationOptions.apiKey || null;
  const resolvedTimeoutMilliseconds =
    clientConfigurationOptions.timeoutMilliseconds ||
    DEFAULT_REQUEST_TIMEOUT_MILLISECONDS;

  return new ApiClient(
    resolvedBaseUrl,
    resolvedApiKey,
    resolvedTimeoutMilliseconds
  );
}

// --- Client Class ---

/**
 * Provides a structured interface for communicating with the remote API.
 *
 * This class encapsulates all HTTP communication logic and provides
 * methods for performing GET and POST requests against the API endpoints.
 */
class ApiClient {
  /**
   * Constructs a new ApiClient.
   *
   * @param {string} baseUrl - The base URL of the API endpoint.
   * @param {string|null} apiKey - The API key used for authentication.
   * @param {number} timeoutMilliseconds - The timeout duration for requests in milliseconds.
   */
  constructor(baseUrl, apiKey, timeoutMilliseconds) {
    this.baseUrl = baseUrl;
    this.apiKey = apiKey;
    this.timeoutMilliseconds = timeoutMilliseconds;
  }

  // --- Request Methods ---

  /**
   * Performs a GET request to the specified API endpoint path.
   *
   * @param {string} endpointPath - The path of the API endpoint to request.
   * @param {Object} queryParameters - The query parameters to include in the request.
   * @returns {Promise<Object>} The parsed response data from the API.
   * @throws {Error} If the request to the API endpoint fails for any reason.
   */
  async getResource(endpointPath, queryParameters = {}) {
    const requestConfiguration = {
      method: "GET",
      url: `${this.baseUrl}${endpointPath}`,
      params: queryParameters,
      timeout: this.timeoutMilliseconds,
      headers: getAuthorizationHeader(this.apiKey),
    };

    logApiRequest(requestConfiguration);

    try {
      const apiResponseData = await axios(requestConfiguration);
      validateApiResponse(apiResponseData);
      return apiResponseData.data;
    } catch (requestError) {
      throw new Error(
        `The request to the API endpoint failed. Please verify that the endpoint ` +
          `"${endpointPath}" is correct and that the service is available. ` +
          `Error details: ${requestError.message}`
      );
    }
  }

  /**
   * Performs a POST request to the specified API endpoint path.
   *
   * @param {string} endpointPath - The path of the API endpoint to request.
   * @param {Object} requestBodyPayload - The body payload to send with the request.
   * @returns {Promise<Object>} The parsed response data from the API.
   * @throws {Error} If the request to the API endpoint fails for any reason.
   */
  async postResource(endpointPath, requestBodyPayload = {}) {
    const requestConfiguration = {
      method: "POST",
      url: `${this.baseUrl}${endpointPath}`,
      data: requestBodyPayload,
      timeout: this.timeoutMilliseconds,
      headers: {
        ...getAuthorizationHeader(this.apiKey),
        "Content-Type": "application/json",
      },
    };

    logApiRequest(requestConfiguration);

    try {
      const apiResponseData = await axios(requestConfiguration);
      validateApiResponse(apiResponseData);
      return apiResponseData.data;
    } catch (requestError) {
      throw new Error(
        `The request to the API endpoint failed. Please verify that the endpoint ` +
          `"${endpointPath}" is correct and that the service is available. ` +
          `Error details: ${requestError.message}`
      );
    }
  }
}

export { createApiClientInstance };
