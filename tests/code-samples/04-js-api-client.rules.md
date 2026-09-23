# Rules Applied: 04-js-api-client

## Pass 1: Code pattern detection
- Factory function (createApiClientInstance) wrapping a plain constructor call
  with three resolved variables that could just be default parameter values -- REMOVE
- Section comments ("// --- Configuration ---", "// --- Factory ---",
  "// --- Client Class ---", "// --- Request Methods ---") -- REMOVE
- JSDoc on every method restating typed parameters that are already self-documenting
- Verbose variable names: requestConfiguration, apiResponseData, requestError,
  requestBodyPayload, endpointPath, clientConfigurationOptions,
  resolvedBaseUrl, resolvedApiKey, resolvedTimeoutMilliseconds
- Import names verbose and mismatched to module content:
  getAuthorizationHeader, formatErrorMessage (unused), logApiRequest,
  validateApiResponse -- imported in alphabetical order, not usage order
- Error messages: full formal sentences with "Please verify..." and
  "Error details:" prefix before re-stating the original error
- Method names verbose and redundant: getResource, postResource (the class is
  already ApiClient, "Resource" adds nothing)
- Constants named with type suffix: DEFAULT_REQUEST_TIMEOUT_MILLISECONDS,
  DEFAULT_API_BASE_URL

## Pass 3: Structural transformation
- Removed factory function entirely; moved defaults into constructor parameters
- Removed all section comments
- Removed all JSDoc blocks
- Shortened method names: getResource -> get, postResource -> post
- Shortened variable names: requestConfiguration -> cfg, apiResponseData -> resp,
  requestError -> err, requestBodyPayload -> body, endpointPath -> path
- Shortened constant names: DEFAULT_API_BASE_URL -> BASE_URL,
  DEFAULT_REQUEST_TIMEOUT_MILLISECONDS -> TIMEOUT
- Shortened import names: getAuthorizationHeader -> authHeader,
  logApiRequest -> logRequest, validateApiResponse -> validateResponse
- Removed unused import (formatErrorMessage)
- Reordered imports by usage order rather than alphabetical order
- Exported ApiClient directly instead of the factory function

## Pass 4: Voice transformation (code)
- Error messages shortened to include the failing value with no filler:
  "The request to the API endpoint failed. Please verify that the endpoint
  \"${endpointPath}\" is correct and that the service is available. Error
  details: ${requestError.message}" -> "GET ${path} failed: ${err.message}"
  and "POST ${path} failed: ${err.message}"
- Method on error message identifies the HTTP verb so the caller knows
  immediately what operation failed and where

## Pass 5: Verification
- Factory pattern: gone, direct construction with defaults -- PASS
- Section comments: none -- PASS
- JSDoc: none; method names (get, post) and parameter names (path, params,
  body) are self-documenting -- PASS
- Variable names: short, idiomatic JS (cfg, resp, err) -- PASS
- Import order: grouped by usage, not alphabet -- PASS
- Error messages: terse, include the failing method and path -- PASS
- No banned vocabulary in any string or comment -- PASS
- No em dashes -- PASS
