# Voice Profile Override: [profile-name]
#
# Place this file at:
#   $XDG_CONFIG_HOME/humanize/voices/<profile>.local.md  (~/.config/humanize/voices/)
#
# Create the directory:
#   mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/humanize/voices"
#
# A copy alongside the installed skill also works, at
# <skill-dir>/reference/voices/<profile>.local.md, but the config directory
# above survives reinstalling the skill and is the better home for a profile
# you plan to keep.
#
# This overrides the built-in profile for that content type only.
# Other profiles are unaffected.
#
# Available profiles: academic, blog, code-comments, code-design, code-docs,
# general, release-notes, rfc, tutorial
#
# Rename this file to match the profile you want to override.
# Example: blog.local.md overrides the blog profile.
#
# Every section below is required. `task voices -- check <profile>` rejects a
# profile that is missing one or leaves one empty, so fill in all ten.

## Register

# How formal or casual? Who is the audience?
# Examples: "informed-casual peer", "formal specification", "patient instructor"
#
# YOUR REGISTER HERE

## Sentence Structure

# Short punchy sentences? Long compound ones? Mix?
# Do you use parenthetical asides? Rhetorical questions?
#
# YOUR PATTERNS HERE

## Voice and Person

# First person? Second person? Active or passive default?
# Do you address the reader directly?
#
# YOUR PREFERENCES HERE

## Directness

# Do you state conclusions flatly or hedge them? Do you use the imperative
# for non-negotiable items? How do you signal disagreement?
#
# YOUR PREFERENCES HERE

## Courtesy

# How much warmth belongs in this voice? The built-ins range from "High
# warmth" (tutorial) to "None to minimal" (rfc). See reference/courtesy.md
# for the line between genuine courtesy and filler.
#
# YOUR LEVEL HERE

## Formatting

# Prose vs lists preference? Bold usage? Heading style?
# How do you use code blocks?
#
# YOUR PREFERENCES HERE

## Vocabulary

# Technical jargon level? Casual language mixed in?
# Terms you use without apology? Terms you avoid?
#
# YOUR PATTERNS HERE

## What This Voice Is NOT

# Which registers should this voice never drift into?
# Examples: corporate speak, academic prose, breathless marketing,
# condescending tutorial tone.
#
# YOUR EXCLUSIONS HERE

## Source

# Links to your own writing that this profile was derived from.
# Use human-authored content only.
#
# - https://your-blog.example.com/some-post
# - https://github.com/your-username/some-repo (pre-LLM-era only)

## Metrics

# Measured targets for this voice. `task voices:profile FROM=<path>` fills
# this in for you; otherwise copy the shape from a built-in profile's
# Target Metrics block and adjust.
#
# sentence_length_mean: 
# sentence_length_sd: 
# first_person_per_1k: 
# second_person_per_1k: 
# contraction_per_1k: 
# em_dash_per_1k: 0
