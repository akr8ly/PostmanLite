# PostmanLite HTTP Test Report

## Summary

PostmanLite's supported REST collection-running workflow was tested against 200 independent local HTTP servers. The execution matrix completed successfully with no failed assertions.

| Metric | Result |
| --- | ---: |
| Dummy HTTP servers | 200 |
| Distinct server ports | 200 |
| Real HTTP requests | 1,421 |
| Assertions | 1,422 |
| Passed | 1,422 |
| Failed | 0 |

## HTTP methods tested

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- `HEAD`
- `OPTIONS`

The unsupported `TRACE` method was also checked and was rejected as expected.

## Scenarios covered

- Requests to every supported method on all 200 servers
- JSON, plain-text, URL-encoded, and text-only form-data request bodies
- Custom headers and query parameters
- Disabled headers and body fields
- Collection variables and response-variable chaining
- Nested collection folders
- Cookies persisted between requests
- Successful and error responses, including `200`, `201`, `204`, `400`, and `500`
- Multi-hop redirects and redirect-limit enforcement
- Slow responses and timeouts
- Abrupt server disconnections
- Unicode text, binary data, malformed JSON, and empty responses

## Result

All 1,422 assertions passed. No functional failures were found in the currently implemented HTTP collection-running workflow. The intentional abrupt-disconnection case produced connection-reset messages on the dummy server side, but PostmanLite handled the failure correctly.

## Known limitations and production risks

The passing result applies to features PostmanLite currently implements. The implementation review identified these limitations and hardening opportunities:

- File fields in Postman form-data requests are not supported.
- Text form-data is sent as URL-encoded data rather than true multipart form-data.
- Duplicate form fields collapse into a single value.
- Postman authentication declarations, GraphQL body mode, scripts, and assertions are not implemented.
- Redirect behavior for `301`, `302`, and `303` may preserve a method and body where some clients switch to `GET`.
- Remote response limits are applied after the response has been downloaded, which can create memory pressure.
- Malformed collection structures need stronger validation and may produce server errors.
- Incoming collection size, run concurrency, and request rate do not yet have explicit production limits.
- DNS-rebinding protection and forwarding of sensitive headers across redirects require additional security hardening.

## Scope note

This was a broad automated compatibility and resilience test, not a formal proof that every possible HTTP server behavior is covered. Protocols and workflows outside the product's current REST-focused scope—such as WebSockets, MQTT, raw TCP, FTP, and Postman scripting—were not treated as supported functionality.

## Test artifact policy

The executable harness, generated JSON data, and other local test artifacts are intentionally excluded from version control through the `tests/` entry in `.gitignore`. This Markdown report is the repository-safe record of the run.
