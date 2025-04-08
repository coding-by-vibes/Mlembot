# ansi_colors.py — Solarized Dark Color Reference for Discord ANSI Blocks

# Reset
RESET = "\u001b[0m"

# ───────────────────────────────────────────────
# 🎨 Foreground Colors
# ───────────────────────────────────────────────
BASE03 = "\u001b[0;30m"   # #002b36 - very dark gray
BASE02 = "\u001b[1;30m"   # #073642 - dark gray (bold black)
BASE01 = "\u001b[0;32m"   # #586e75 - greenish gray
BASE00 = "\u001b[0;33m"   # #657b83 - yellow-gray
BASE0  = "\u001b[0;34m"   # #839496 - blue-gray
BASE1  = "\u001b[0;36m"   # #93a1a1 - cyan-gray
BASE2  = "\u001b[0;37m"   # #eee8d5 - light tan
BASE3  = "\u001b[1;37m"   # #fdf6e3 - off-white

# ───────────────────────────────────────────────
# 🌈 Accent Colors (Foreground)
# ───────────────────────────────────────────────
SOL_YELLOW  = "\u001b[1;33m"  # #b58900
SOL_ORANGE  = "\u001b[0;31m"  # #cb4b16
SOL_RED     = "\u001b[1;31m"  # #dc322f
SOL_MAGENTA = "\u001b[1;35m"  # #d33682
SOL_VIOLET  = "\u001b[0;35m"  # #6c71c4
SOL_BLUE    = "\u001b[1;34m"  # #268bd2
SOL_CYAN    = "\u001b[1;36m"  # #2aa198
SOL_GREEN   = "\u001b[1;32m"  # #859900

# ───────────────────────────────────────────────
# 🖋 Underlined Variants
# ───────────────────────────────────────────────
UNDER_BASE1  = "\u001b[4;36m"
UNDER_SOL_YELLOW = "\u001b[4;33m"
UNDER_SOL_RED    = "\u001b[4;31m"
UNDER_SOL_GREEN  = "\u001b[4;32m"
UNDER_SOL_CYAN   = "\u001b[4;36m"

# ───────────────────────────────────────────────
# 🧱 Background Colors (approximated)
# ───────────────────────────────────────────────
BG_BASE03 = "\u001b[0;40m"  # background black
BG_BASE02 = "\u001b[0;44m"  # background blue-gray
BG_BASE01 = "\u001b[0;42m"  # background greenish
BG_BASE00 = "\u001b[0;43m"  # background yellowish
BG_BASE0  = "\u001b[0;46m"  # background cyan
BG_BASE1  = "\u001b[0;47m"  # background light
BG_SOL_RED     = "\u001b[0;41m"
BG_SOL_BLUE    = "\u001b[0;44m"
BG_SOL_MAGENTA = "\u001b[0;45m"

# ───────────────────────────────────────────────
# 🧪 Sample Combinations
# ───────────────────────────────────────────────
BULLET         = f"{SOL_GREEN}•{RESET}"
BULLET_SUB     = f"{BASE0}→{RESET}"
TITLE_COLOR    = SOL_CYAN
HEADER_COLOR   = SOL_YELLOW
QUOTE_COLOR    = SOL_MAGENTA
TEXT_COLOR     = BASE1

