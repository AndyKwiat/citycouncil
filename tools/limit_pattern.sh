# Shared by the batch scripts: what a real usage or rate limit looks like in a log. Bare numbers like "1,429 tokens"
# must not match, so 429 only counts next to HTTP/status/error wording.
LIMIT='usage limit|limit reached|hit your limit|out of (extra )?usage|credit balance|weekly limit|session limit|rate limit|overloaded|(HTTP|status|error|code)[ :=]*429|429 Too Many'
