# Code-Specific AI Detection Patterns

Patterns that distinguish AI-generated code from human-written code. Used during
Humanize code transformation passes.

---

## Detection Dimensions

### 1. Naming Conventions

**AI pattern:** Uniformly verbose, descriptive names everywhere.
```python
# AI-generated
user_authentication_service = UserAuthenticationService()
database_connection_manager = DatabaseConnectionManager()
request_validation_middleware = RequestValidationMiddleware()
```

**Human pattern:** Mix of descriptive and abbreviated names based on scope and
context. Longer names for public APIs, shorter for local variables.
```python
# Human-written
auth = AuthService()
db = DBManager()
validator = RequestValidator()  # or just 'mw' in a file that's clearly about middleware
```

**Transformation rule:** Shorten local variables and well-understood abbreviations.
Keep descriptive names for public interfaces and configuration. Match the
project's existing conventions.

---

### 2. Comment Density and Style

**AI pattern:** Comments on every function, class, and non-trivial block.
Formal, uniform style. Often restates what the code does.
```python
# AI-generated
def calculate_total(items):
    """Calculate the total price of all items in the cart.

    Args:
        items: A list of Item objects with price attributes.

    Returns:
        float: The total price of all items.
    """
    total = 0.0  # Initialize total to zero
    for item in items:  # Iterate through each item
        total += item.price  # Add item price to total
    return total  # Return the calculated total
```

**Human pattern:** Comments explain *why*, not *what*. Sparse where code is
self-explanatory. Informal tone.
```python
# Human-written
def calculate_total(items):
    # NOTE: doesn't include tax -- that's handled at checkout
    return sum(item.price for item in items)
```

**Transformation rule:** Remove comments that restate code. Keep comments that
explain why, warn about gotchas, or mark TODOs. Match the project's comment
style.

**Exception:** Keep "what" comments in three cases:

1. **Dense syntax:** Regexes, bitwise operations, complex comprehensions, and
   similar constructions where a human can't grasp intent at a glance. A comment
   like `# Remove YAML frontmatter` above `re.sub(r'^---\n.*?\n---\n', ...)` is
   not restating the obvious.
2. **Transform chains:** When every step in a pipeline has a comment, the
   comments form a narrative. Removing one breaks the pattern and makes the
   remaining steps harder to follow. Keep or delete the whole set together.
3. **Section markers in long functions:** Comments like `# Build the profile`
   that act as headings inside a 40+ line function help humans scan the
   structure. These aren't explaining a single line; they're organizing a block.

---

### 3. Error Handling

Scope: control flow. Which exceptions get caught, how narrowly, and which edge
cases are covered. The wording inside the message is dimension #5.

**AI pattern:** Handles common cases with generic, grammatically complete error
messages. Misses edge cases.
```python
# AI-generated
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.exceptions.RequestException as e:
    raise ConnectionError(
        f"Failed to connect to the remote server. "
        f"Please check your network connection and try again. "
        f"Error details: {e}"
    )
```

**Human pattern:** Terse error messages. Handles edge cases. May include
context about what was being attempted.
```python
# Human-written
try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
except requests.ConnectionError:
    raise ConnectionError(f"can't reach {url}")
except requests.Timeout:
    raise TimeoutError(f"{url} timed out after 30s")
```

**Transformation rule:** Split generic exception handlers into specific ones.
Add the edge case handling that is missing. Leave message wording to #5. When
one `except` block needs both a narrower catch and a shorter message, that is
two findings, one per dimension, because the two are fixed independently.

---

### 4. Import Organization

**AI pattern:** Perfectly grouped, alphabetically sorted, with clear section
comments.
```python
# AI-generated
# Standard library imports
import json
import os
import sys
from pathlib import Path

# Third-party imports
import requests
from flask import Flask, jsonify, request

# Local imports
from .config import Settings
from .models import User
from .utils import validate_input
```

**Human pattern:** Roughly grouped but ordered by when they were added or by
logical usage. No section comments unless the file is large.
```python
# Human-written
import os
import sys
import json
from pathlib import Path

import requests
from flask import Flask, request, jsonify

from .models import User
from .config import Settings
from .utils import validate_input
```

**Transformation rule:** Keep logical grouping but relax alphabetical ordering.
Remove section comments unless the import list is genuinely long (20+ lines).

---

### 5. Error Messages

Scope: wording. The text a user or a log reader ends up seeing, whichever
handler produced it. Which exceptions get caught is dimension #3.

**AI pattern:** Full sentences, formal grammar, helpful suggestions.
```
"Authentication failed. Please verify your credentials and ensure your account is active."
"The specified file could not be found. Please check the file path and try again."
```

**Human pattern:** Terse, contextual, sometimes includes the failing value.
```
"auth failed"
"file not found: /etc/foo/bar.conf"
"bad config: expected integer for 'port', got 'abc'"
```

**Transformation rule:** Shorten to essential information. Include the failing
value when diagnostic. Drop "please" and suggestions unless it's a user-facing
CLI tool.

---

### 6. Structural Patterns

**AI pattern:** Perfect separation of concerns. Every function does one thing.
Factory patterns and abstractions even for one-time operations.
```python
# AI-generated
class ConfigLoaderFactory:
    @staticmethod
    def create_loader(config_type):
        if config_type == "yaml":
            return YAMLConfigLoader()
        elif config_type == "json":
            return JSONConfigLoader()
        raise ValueError(f"Unsupported config type: {config_type}")
```

**Human pattern:** Pragmatic. Abstractions emerge from need, not anticipation.
```python
# Human-written
def load_config(path):
    if path.endswith('.yaml') or path.endswith('.yml'):
        return yaml.safe_load(open(path))
    return json.load(open(path))
```

**Transformation rule:** Flatten unnecessary abstractions. Inline one-caller
helpers. Keep abstractions that serve 3+ callers or genuinely complex logic.

---

### 7. Whitespace and Formatting

**AI pattern:** Consistent, generous whitespace. Blank lines between every
logical block.

**Human pattern:** Pragmatic spacing. Tighter grouping of related operations.
Occasional inconsistency.

**Transformation rule:** Tighten spacing where operations are closely related.
Allow minor inconsistencies that don't harm readability.

---

### 8. Commit Patterns

This isn't about transforming code but about how the code is delivered.
`SKILL.md` routes Pass 2 through all eight dimensions, so read this one as a
delivery-stage check: dimensions 1 through 7 change the contents of files,
this one changes how you land them. Findings here are guidance for the next
commit, not edits to make in the working tree.

**AI pattern:** Large chunks committed at once with vague messages.
```
"Add user authentication system"
"Implement database connection handling"
```

**Human pattern:** Iterative, small commits with specific messages.
```
"add basic auth middleware"
"wire auth middleware into /api routes"
"handle token refresh on 401"
"fix: auth middleware was skipping OPTIONS requests"
```

**Transformation rule:** Guide iterative commits. The Humanize skill should
encourage committing at logical checkpoints, not transforming commit history.

---

## Sources

- BlueOptima, "How to Detect AI-Generated Code" (2025)
- HackerRank, "How HackerRank Catches AI-Generated Code" (2025)
- Span, "AI Code Detector" -- span-detect-1 model documentation (2025)
- CodeDetector.io, "How to Detect AI-Generated Code in 2025" (2025)
- EX-CODE: Explainable Model to Detect AI-Generated Code, MDPI (2024)
