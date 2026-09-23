# Rules Applied: 01-auth-service

## Pass 1: Code pattern detection
- Module docstring: Formal, restates obvious purpose -- REMOVE
- Class docstring: Verbose, mentions "leverages" and "industry-standard" -- REMOVE
- Method docstrings: Restate parameters that are self-documenting -- REMOVE
- Inline comments: Nearly every line commented with what, not why -- REMOVE most
- Variable names: Uniformly verbose (user_repository, token_generation_service,
  database_connection_manager, user_identifier, token_expiration_minutes)
- Error messages: Full sentences with "Please try again" suggestions
- Imports: Perfectly alphabetized with unused imports (json, os, secrets, time, etc.)
- Dataclass fields: Overly verbose (is_authenticated, user_identifier, etc.)

## Pass 3: Structural transformation
- Removed module docstring (module name is self-documenting)
- Removed class docstring (class name + methods are clear)
- Removed all method docstrings (parameters are typed, names are clear)
- Removed inline comments that restate code
- Removed unused imports (json, os, secrets, time, Dict, List, Tuple)
- Shortened variable names: user_repository -> users, token_generation_service
  -> tokens, database_connection_manager -> db, user_identifier -> user_id,
  token_expiration_minutes -> token_ttl_min, max_login_attempts -> max_attempts
- Shortened class names: AuthenticationResult -> AuthResult,
  AuthenticationService -> AuthService
- Shortened method names: authenticate_user -> authenticate,
  _verify_password -> _check_password
- Shortened import aliases to match abbreviated conventions

## Pass 4: Voice transformation (code)
- Error messages shortened: "Authentication failed. Please check your
  credentials and try again." -> "bad credentials"
- "Your account has been locked due to too many failed login attempts..." ->
  "account locked"
- Exception message: long formal message -> "auth failed: {exc}"
- Added `from exc` to exception chain (a detail AI often misses)
- Used %s formatting in logger calls (idiomatic for logging module)
- Used 100_000 numeric separator (minor readability preference)

## Pass 5: Verification
- Naming: abbreviated where clear, descriptive for public API -- PASS
- Comments: zero restating comments, kept security-relevant constant-time
  comparison (code is self-documenting here) -- PASS
- Error messages: terse, contextual -- PASS
- Imports: only what's used, logically grouped -- PASS
- No over-engineering: no factory patterns, no unnecessary abstractions -- PASS
- Exception chaining: properly chains with `from exc` -- PASS
