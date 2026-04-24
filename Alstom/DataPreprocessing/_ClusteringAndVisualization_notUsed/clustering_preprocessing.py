# -*- coding: utf-8 -*-
"""
Created on Sun Feb 15 19:47:03 2026

@author: chodo
"""
import re
from pathlib import Path

# -------------------------
# Regex building blocks
# -------------------------
MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
DOW = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"

# IPv4 (keep simple; good enough)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

# 1) ISO timestamps: 2021-12-16 10:20:06(.mmm)?
TIME_ISO_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\b")

# 2) Short: 21-12-16 10:20:13(.mmm)?
TIME_SHORT_RE = re.compile(r"\b\d{2}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?\b")

# 3) Textual with DOW: Thu Dec 16 10:20:10 2021   (UTC optional)
TIME_TEXT_WITH_DOW_RE = re.compile(
    rf"\b{DOW}\s+{MONTHS}\s+\d{{1,2}}\s+\d{{2}}:\d{{2}}:\d{{2}}(?:\s+UTC)?\s+\d{{4}}\b"
)

# 4) Syslog-like without year: Mar  7 22:02:02   (note double space possible before 7)
TIME_SYSLOG_RE = re.compile(
    rf"\b{MONTHS}\s+\d{{1,2}}\s+\d{{2}}:\d{{2}}:\d{{2}}\b"
)

# Optional date-only (if you still want it)
DATE_ONLY_RE = re.compile(r"\b(?:\d{4}|\d{2})-\d{2}-\d{2}\b")

# Hex patterns:
# - explicit 0x... anywhere
# - long hex blobs (>=8)
HEX_0X_RE = re.compile(r"\b0x[0-9a-fA-F]+\b")
HEX_LONG_RE = re.compile(r"\b[0-9a-fA-F]{8,}\b")

# Special: "hex: 0x..." (with optional spaces)
HEX_FIELD_RE = re.compile(r"\bhex\s*:\s*(0x[0-9a-fA-F]+)\b", re.IGNORECASE)

# Paths:
# - Unix absolute paths: /usr/bin/thing, /var/log/.., /opt/a-b_c
# - Windows paths: C:\Users\...\file.log or \\server\share\file
UNIX_PATH_RE = re.compile(r"(?<!\w)(/[^ \t\r\n]+)")
WIN_PATH_RE = re.compile(r"(?<!\w)([A-Za-z]:\\[^ \t\r\n]+|\\\\[^ \t\r\n]+)")

# Stack frame line:
# "2: ./HmiRuntime() [0x80d5f18]" -> "<num>: <fun> [<hex>]"
STACK_FRAME_RE = re.compile(
    r"^\s*(\d+)\s*:\s*(.*?)\s*\[\s*(0x[0-9a-fA-F]+|[0-9a-fA-F]{8,})\s*\]\s*$"
)

# Numbers (after time/ip/hex are handled)
NUM_RE = re.compile(r"\b\d+\b")

# Message level words, preserving case differences as distinct tokens
LEVEL_WORDS = ["NOTICE", "INFO", "WARNING", "ERROR", "FATAL"]
LEVEL_RE = re.compile(
    r"\b(" + "|".join(LEVEL_WORDS) + r")\b",
    re.IGNORECASE
)



# --- New: quoted strings (single quotes) -> <str> ---
# Matches: 'SubsystemBitPosition_0', 'ProjectName', etc.
SINGLE_QUOTED_STR_RE = re.compile(r"'[^'\r\n]*'")

# --- New: bracketed logger/component -> [<var>] ---
# Specifically targets: [Configuration.LogicalName]
VAR_RE = re.compile(
    r"\b[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\b"          # dot-style (Configuration.LogicalName)
    r"|"
    r"\b[A-Za-z][A-Za-z0-9_]*_[A-Za-z0-9_]+\b"                # underscore-style (SubsystemBitPosition_0)
    r"|"
    r"\b[A-Za-z_]\w*(?:::[A-Za-z_]\w*)+\b(?!\s*\()"           # scope-style (A::B::C) but NOT if followed by '('
)


# Function-ish tokens:
# - ./HmiRuntime()
# - HmiRuntime()
# - something::method(...)
# - allow dots/colons/underscores in names
FUN_RE = re.compile(r"\b(?:\./)?[A-Za-z_][\w.:<>~+-]*\s*\([^)]*\)")

# FINAL STEP for <text>
TOKEN_RE = re.compile(r"<[^>\r\n]+>")   # matches <time>, <MSG_TITLE>, <var>, etc.
TEXT_RE = re.compile(r"[A-Za-z_]+")     # aggressive: any remaining letters -> <text>
PUNCT_REMOVE_RE = re.compile(r"[.,!?;]")
MULTI_TEXT_RE = re.compile(r"(?:<text>\s*){2,}")
WHITELIST_WORDS = {"SIGNAL", "variable", "communication", "Configuration"}

#WHITELIST_WORDS = {"uic", "policy", "train", "could", "available", "runtime", "port", "stop"}
"""{
    "Arg",
    "Stacktrace",
    "SIGNAL",
    "MAIN",
    "hex"
    ,"Runtime"
    ,"linux"
    ,"Crash"
    , "Trace"
    , "Configuration"
    , "log"
    , "Failed"
    , "Start"
    # add anything you want here
}"""


TOKEN_WHITELIST = {"<num>", "<fun>", "<hex>", "<text>", "<MSG>", "<time>", "<var>", "<path>", "<ip>"}

WORD_RE = re.compile(r"(?<!<)\b[A-Za-z]+\b(?!>)")
TOKEN_COLLAPSE_RE = re.compile(r"(<[^>\s]+>)(?:\s+\1)+")

TOKEN_ONLY_RE = re.compile(r"<[^>\s]+>")

def normalize_line(line: str) -> str:
    s = line.rstrip("\n")
    # 0) If it is a stack-frame line, normalize in a targeted way
    m = STACK_FRAME_RE.match(s)
    if m:
        # We intentionally do not keep the original function string; we collapse it.
        return "<num>: <fun> [<hex>]"

    # 1) Replace times (do before numbers)
    s = TIME_ISO_RE.sub("<time>", s)
    s = TIME_SHORT_RE.sub("<time>", s)
    s = TIME_TEXT_WITH_DOW_RE.sub("<time>", s)
    s = TIME_SYSLOG_RE.sub("<time>", s)
    s = DATE_ONLY_RE.sub("<time>", s)  # optional; keep if helpful

    # 2) Replace IPs
    s = IP_RE.sub("<ip>", s)

    # 3) Replace paths (do before function; avoids turning "/usr/bin/x(y)" into <fun>)
    s = WIN_PATH_RE.sub("<path>", s)
    s = UNIX_PATH_RE.sub("<path>", s)

    # 4) Improve hex handling:
    #   - normalize "hex: 0x..." field
    #   - normalize other 0x... tokens
    #   - normalize long hex blobs
    s = HEX_FIELD_RE.sub("hex: <hex>", s)
    s = HEX_0X_RE.sub("<hex>", s)
    s = HEX_LONG_RE.sub("<hex>", s)
    
    # 4.5) Replace single-quoted strings early so digits inside don't become <num>
    s = SINGLE_QUOTED_STR_RE.sub("<text>", s)
    
    # 6) Replace message level words with case-sensitive tokens
    # We intentionally ignore which exact level it was (INFO vs ERROR) at this stage,
    # since you asked to replace them all by a <MSG*> token.
    s = LEVEL_RE.sub("<MSG>", s)
    
    # 5) Replace function-like calls (after paths)
    # This is intentionally coarse: we want format, not semantics.
    s = FUN_RE.sub("<fun>", s)   # first
    s = VAR_RE.sub("<var>", s)   # then

    # 7) Replace remaining numbers
    s = NUM_RE.sub("<num>", s)
    
    # ---------------------------------------------------------
    # SYMBOL STRIPPING STAGE (before <text> abstraction)
    # ---------------------------------------------------------
    # Remove everything except:
    # - letters A-Z / a-z
    # - whitespace
    # - angle brackets (to preserve tokens)
    s = re.sub(r"[^A-Za-z<>\s:\[\]=()]", " ", s)
    
    
    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # ---------------------------------------------------------
    # FINAL ABSTRACTION STEP (no stashing)
    # ---------------------------------------------------------
    
    # Remove punctuation/symbols if you want (your symbol stripping already did most)
    s = re.sub(r"[.,!?;_]", "", s)
    
    # Convert remaining words to <text>, except whitelist words
    def word_to_text(m: re.Match) -> str:
        w = m.group(0)
        return w if w in WHITELIST_WORDS else "<text>"
    
    s = WORD_RE.sub(word_to_text, s)
    
    s = s.replace("<", " <").replace(">", "> ").replace("[", " [").replace("]", "] ").replace("::", "").replace(":", " : ")

    # Normalize whitespace
    s = re.sub(r"\s+", " ", s).strip()
    
    # ---------------------------------------------------------
    # FINAL STRICT FILTER
    # ---------------------------------------------------------
    allowed = set(TOKEN_WHITELIST) | set(WHITELIST_WORDS) | set({":", "[", "]"})
    
    words = s.split()
    s = " ".join([w for w in words if w in allowed])
    prev = None
    while prev != s:
        prev = s
        s = TOKEN_COLLAPSE_RE.sub(r"\1", s)
    return s


if __name__ == "__main__":
    import main_cluster
    main_cluster.main()