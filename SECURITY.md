# Security Policy

Humanize ships prompts, reference tables, and a handful of Python and shell
helpers that run on your own machine. There is no server, no hosted component,
and no account. That shapes what a vulnerability in this project looks like, so
this document covers three things: how to report one, what the module touches
when it runs, and where the project stands on acceptable use.

## Reporting a vulnerability

Report privately through GitHub. Open the repository's **Security** tab and
choose **Report a vulnerability**. That opens an advisory visible only to you
and the maintainers.

Please don't open a public issue for a suspected vulnerability, and don't post
details to a discussion thread or a social account before the advisory is
resolved.

A useful report names the affected file or command, the commit or release you
tested, and the steps that reproduce the behavior. Add your platform and Python
version when the problem looks environment-dependent. A proof of concept helps,
but a clear description of the flaw is enough to start.

### What to expect

This is a small project with no funded security function. The targets below are
commitments to communicate, not to a fixed engineering schedule.

| Stage | Target |
|-------|--------|
| Acknowledgement | 7 days |
| Initial assessment | 30 days |
| Fix, or a documented decision not to fix | 90 days |

You'll be told which category the report falls into and why. If it turns out to
describe a deliberate design decision rather than a defect, you get the
reasoning instead of silence. Reporters are credited in the advisory unless
they ask not to be.

### Supported versions

Fixes land on `main` and in the next release. The project is pre-1.0 and
nothing is backported to earlier tags, so upgrading is the remediation path if
you pin a commit.

## What counts

The interesting question for a local text tool is which inputs it trusts. The
sections below describe where untrusted data enters, what the existing controls
are, and what residual risk you accept by running each part.

### Content you humanize

The skill reads the files you point it at and passes their contents to an AI
assistant. Any text in those files reaches the model, including text written to
manipulate it. A document that contains instructions aimed at the assistant is
a live prompt-injection vector, and batch mode widens it by handing files to
subagents.

Treat this the way you'd treat piping an untrusted file into any AI tool. If
you're humanizing a pull request from a stranger, read it first. The skill
guards your files rather than your model context: `humanize-branch.sh` refuses
to run against a dirty worktree, so every change a run makes is uncommitted and
`git checkout -- .` puts you back where you started.

### Sources fetched from the internet

`scripts/update-sources.sh` downloads the research pages listed in its own
registry, plus any URL you add to `personal-sources.yml`. Fetches use `curl`
over HTTPS with a 30-second timeout and follow redirects. Responses land in
`.test-output/` and are parsed as text. There's no cap on response size, so a
hostile or broken endpoint can fill that directory.

The registry entries are maintainer-controlled and the command only runs when
you ask for it. The part worth your attention is `personal-sources.yml`,
because that file is yours. Values from it are parsed through Python into JSON
and never evaluated by the shell; `tests/test_security.py` covers command
substitution, backticks, and semicolons in source descriptions. Adding a URL
you don't trust is still your decision to make.

### Documents parsed on your disk

`scripts/extract-text.py` shells out to `pdftotext` for PDFs and `pandoc` for
DOCX, ODT, EPUB, RTF, and LaTeX. Both run through `subprocess.run` with
argument lists rather than a shell string, and both carry timeouts, so filenames
can't break out into shell syntax.

What you inherit is the safety of those parsers. Poppler and pandoc have both
had memory-safety and file-inclusion issues over the years, and pointing a
voice profile run at a directory of untrusted documents feeds them straight
into those parsers. Keep the system packages current, and prefer running voice
generation over writing you produced yourself, which is what the feature is for
anyway.

### Models downloaded for detection

The optional detection path in `scripts/detect.py` pulls models from Hugging
Face and caches them under `~/.cache/huggingface/`. `BINOCULARS_OBSERVER` and
`BINOCULARS_PERFORMER` let you name a different repository, which means an
environment variable chooses what gets downloaded and loaded.

`trust_remote_code` is never passed, so it stays at the `transformers` default
of off. That matters: with it off the library loads weights and configuration
but won't execute Python shipped inside a model repository, which is the
difference between downloading a bad model and running one. Treat it as a
setting this project relies on. Don't turn it on, and don't accept a patch that
does.

### Files the module writes

`manage-voices.py` reads, writes, and deletes profile overrides under
`$XDG_CONFIG_HOME/humanize/voices/`, defaulting to `~/.config/humanize/voices/`.
Every subcommand that resolves a profile type checks it against an allowlist
built from the built-in profile filenames, so a traversal string like
`../../.ssh/id_rsa` fails the check before any path is constructed. Deletion
can only reach `<voices-dir>/<known-type>.local.md`.

Beyond that directory, the module writes to `.test-output/` and to the branch
it created for you.

## What is not a vulnerability

Some reports are better filed as ordinary issues:

- Output quality. A missed pattern, an awkward rewrite, or a skill that didn't
  trigger is a bug, not a security defect.
- Detection scores. How a sample scores against Binoculars, GLTR, or any
  commercial classifier is a research question, and the baselines in
  `tests/detection-baselines.yml` exist to track it.
- Upstream flaws in `pandoc`, `pdftotext`, `torch`, or `transformers`. Report
  those to their maintainers. Do tell us if Humanize invokes them unsafely.
- Attacks that assume the attacker already controls your machine, your shell
  environment, or your `personal-sources.yml`.
- The observation that the module can be used to obscure AI authorship. That is
  what it does, and the next section explains the position.

## Acceptable use

Humanize rewrites text so it reads as though a person wrote it. Used against
material an LLM drafted, that plainly makes the origin harder to spot. The
project would rather say so than pretend otherwise.

The README lists what the module doesn't attempt: no artificial errors, no
watermark evasion, no promise that any classifier will return a particular
verdict. Those aren't disclaimers bolted on after the fact. Statistical
detectors are unreliable in both directions, and their false positives fall
hardest on non-native English speakers, who get flagged for writing plainly. A
detector score was never sound evidence of authorship, which is why this project
doesn't measure itself by one and why "beat the detector" isn't a feature
request we'll take.

The intended use is voice, not concealment. You draft with a model, the prose
comes out flattened into the register every model shares, and this module puts
it back into yours. Editing your own writing has never required anyone's
permission.

Misrepresenting authorship where disclosure is required or expected is a
different act, and the project doesn't sanction it. Academic submissions,
journalism, legal filings, and any context with a stated disclosure policy all
fall on that side of the line. An MIT-licensed text tool that runs on your
laptop has no way to enforce this, and claiming otherwise would be theater. The
position is a position, and you should read it as one.

The project holds itself to the same standard. The README carries an explicit
notice that Humanize was built with AI assistance, in the place a reader looks
first.
