"""
Schema constructors and the full SECTIONS catalogue.

This module is pure Python – it never imports sublime so it can be imported
safely during early plugin load and in unit-test environments.

Public API
----------
b, e, n, s, j, pk, rp, lp  – entry constructor helpers
SECTIONS                     – ordered list of (title, [entry, ...]) tuples
KEY_INDEX                    – flat dict mapping setting key → entry dict
esc, short, norm_choices     – pure HTML/string utilities used by the renderer
"""

# ---------------------------------------------------------------------------
# Entry constructor helpers
# ---------------------------------------------------------------------------

def b(k, t, d, df):
    """Boolean (checkbox) setting."""
    return {"key": k, "title": t, "desc": d, "type": "bool", "default": df}


def e(k, t, d, df, ch):
    """Enum (radio) setting."""
    return {"key": k, "title": t, "desc": d, "type": "enum", "default": df, "choices": ch}


def n(k, t, d, df, presets=None, step=1, is_float=False):
    """Numeric (stepper) setting."""
    return {"key": k, "title": t, "desc": d, "type": "number", "default": df,
            "presets": presets, "step": step, "is_float": is_float}


def s(k, t, d, df, presets=None):
    """String setting (edited via input panel)."""
    return {"key": k, "title": t, "desc": d, "type": "string", "default": df,
            "presets": presets}


def j(k, t, d, df):
    """JSON setting (edited via input panel)."""
    return {"key": k, "title": t, "desc": d, "type": "json", "default": df}


def pk(k, t, d, df, cmd):
    """Picker – opens a native Sublime command (e.g. select_color_scheme)."""
    return {"key": k, "title": t, "desc": d, "type": "picker", "default": df, "cmd": cmd}


def rp(k, t, d, df, kind):
    """Resource picker – quick-panel of .sublime-theme / .sublime-color-scheme resources."""
    return {"key": k, "title": t, "desc": d, "type": "respick", "default": df, "kind": kind}


def lp(k, t, d, df, provider):
    """List picker – quick-panel backed by a named PROVIDERS entry (e.g. 'fonts')."""
    return {"key": k, "title": t, "desc": d, "type": "listpick", "default": df,
            "provider": provider}


# ---------------------------------------------------------------------------
# Settings catalogue
# ---------------------------------------------------------------------------

SECTIONS = [
    ("APPEARANCE \u203a COLOR SCHEME", [
        pk("color_scheme", "Color Scheme",
           "Colors used within the text area. Opens the native picker.",
           "Mariana.sublime-color-scheme", "select_color_scheme"),
        rp("light_color_scheme", "Light Color Scheme",
           "Used when color_scheme is \"auto\".",
           "Breakers.sublime-color-scheme", "color_scheme"),
        rp("dark_color_scheme", "Dark Color Scheme",
           "Used when color_scheme is \"auto\".",
           "Mariana.sublime-color-scheme", "color_scheme"),
    ]),
    ("APPEARANCE \u203a FONT", [
        lp("font_face", "Font Face", "Editor font. Pick from installed fonts.", "", "fonts"),
        n("font_size", "Font Size", "Editor font size in points.", 10,
          presets=[10, 12, 14, 16, 18], step=1),
        n("default_font_size", "Default Font Size", "Size applied by \"Reset Size\".", 10, step=1),
        j("font_options", "Font Options", "Rendering flags (e.g. no_bold, gray_antialias).", []),
        j("theme_font_options", "Theme Font Options", "Font options for theme text.", []),
    ]),
    ("APPEARANCE \u203a THEME", [
        pk("theme", "Theme", "Look of Sublime's UI. Opens the native picker.",
           "auto", "select_theme"),
        rp("light_theme", "Light Theme", "Used when theme is \"auto\".",
           "Default.sublime-theme", "theme"),
        rp("dark_theme", "Dark Theme", "Used when theme is \"auto\".",
           "Default Dark.sublime-theme", "theme"),
        b("themed_title_bar", "Themed Title Bar", "Use a custom title bar (adaptive theme).", True),
        e("file_tab_style", "File Tab Style", "Style of file tabs.", "rounded",
          ["rounded", "square", "angled"]),
        b("inactive_sheet_dimming", "Inactive Sheet Dimming",
          "Dim inactive sheets for focus.", True),
        b("tree_animation_enabled", "Tree Animation",
          "Animate sidebar folder expand/collapse.", True),
        b("animation_enabled", "Animation", "Animation throughout the app.", True),
        b("highlight_modified_tabs", "Highlight Modified Tabs",
          "Make modified-file tabs more visible.", False),
        b("show_tab_close_buttons", "Tab Close Buttons", "Show the tab close button.", True),
        b("show_tab_close_buttons_on_left", "Close Buttons On Left",
          "Place close buttons on the left.", False),
        b("bold_folder_labels", "Bold Folder Labels", "Show sidebar folders in bold.", False),
        b("adaptive_dividers", "Adaptive Dividers", "Divider lines between UI sections.", False),
        b("popup_shadows", "Popup Shadows", "Draw shadows under popups.", True),
        e("native_tabs", "Native Tabs (Mac)", "macOS native tab behavior.", "system",
          ["system", "preferred", "disabled"]),
        b("open_tabs_after_current", "Open Tabs After Current",
          "New tabs open after the current tab.", True),
        e("overlay_scroll_bars", "Overlay Scroll Bars", "Overlay scroll bar behavior.", "system",
          ["system", "enabled", "disabled"]),
        b("enable_tab_scrolling", "Tab Scrolling", "Scroll tabs instead of shrinking.", True),
        b("hide_tab_scrolling_buttons", "Hide Tab Scroll Buttons",
          "Hide the tab scroll buttons.", False),
        b("hide_new_tab_button", "Hide New Tab Button", "Hide the new tab button.", False),
        b("show_sidebar_button", "Sidebar Button",
          "Toggle-sidebar button in the status bar.", True),
        b("sidebar_on_right", "Sidebar On Right", "Move the sidebar to the right.", False),
        n("ui_scale", "UI Scale", "Magnify the UI (0 = auto). Needs restart.",
          0.0, step=0.5, is_float=True),
        e("hardware_acceleration", "Hardware Acceleration", "GPU rendering. Needs restart.",
          "none", ["none", "opengl"]),
    ]),
    ("EDITOR \u203a GUTTER", [
        b("line_numbers", "Show Line Numbers", "Draw line numbers in the gutter.", True),
        b("relative_line_numbers", "Relative Line Numbers",
          "Draw distance from the current line.", False),
        b("gutter", "Show Gutter", "Show the gutter altogether.", True),
        n("margin", "Gutter Margin", "Spacing between the gutter and the text.", 4, step=1),
        b("fold_buttons", "Fold Buttons", "Triangles in the gutter to fold regions.", True),
        b("fade_fold_buttons", "Fade Fold Buttons",
          "Hide fold buttons unless hovering the gutter.", True),
        e("fold_style", "Fold Style", "Code folding strategy.", "auto",
          ["auto", "force_indentation", "scope_only"]),
        e("mini_diff", "Modified Line Markers", "Indicate modified lines in the gutter.", True,
          [(True, "On"), ("auto", "Auto"), (False, "Off")]),
    ]),
    ("EDITOR \u203a RULERS", [
        j("rulers", "Rulers", "Columns at which to draw vertical rulers.", []),
        e("ruler_style", "Ruler Style", "How ruler lines are drawn.", "dotted",
          ["dotted", "stippled", "solid"]),
        n("ruler_width", "Ruler Width", "How wide ruler lines are drawn.", 1.0,
          step=0.5, is_float=True),
    ]),
    ("EDITOR \u203a INDENTATION", [
        n("tab_size", "Tab Width", "Number of spaces a tab is equal to.", 4,
          presets=[2, 4, 8], step=1),
        b("translate_tabs_to_spaces", "Insert Spaces", "Insert spaces when Tab is pressed.", False),
        b("use_tab_stops", "Use Tab Stops", "Tab/backspace move to the next tab stop.", True),
        b("detect_indentation", "Detect Indentation", "Detect tabs vs. spaces on load.", True),
        b("auto_indent", "Auto Indent", "Calculate indentation when pressing enter.", True),
        b("smart_indent", "Smart Indent", "Smarter auto indent (e.g. after an if).", True),
        b("indent_to_bracket", "Indent To Bracket",
          "Indent up to the first open bracket.", False),
        b("trim_automatic_white_space", "Trim Automatic White Space",
          "Trim whitespace added by auto indent.", True),
        b("draw_indent_guides", "Indent Guides", "Draw indentation guides.", True),
        j("indent_guide_options", "Indent Guide Options", "How indent guides are drawn.",
          ["draw_normal"]),
        b("shift_tab_unindent", "Shift+Tab Unindents", "Always unindent on shift+tab.", False),
    ]),
    ("EDITOR \u203a WORD WRAP", [
        e("word_wrap", "Word Wrap", "Wrap long lines.", "auto",
          [(True, "On"), (False, "Off"), ("auto", "Auto")]),
        n("wrap_width", "Wrap Width", "Force wrapping at this column (0 = window width).",
          0, step=1),
        e("wrap_width_style", "Wrap Width Style", "How wrap_width is applied.", "constant",
          ["constant", "min"]),
        b("indent_subsequent_lines", "Indent Wrapped Lines",
          "Indent wrapped lines to the same level.", True),
        b("draw_centered", "Draw Centered", "Center text in the window.", False),
    ]),
    ("EDITOR \u203a BRACKETS & TAGS", [
        b("auto_match_enabled", "Auto Match", "Auto pair quotes, brackets, etc.", True),
        b("auto_close_tags", "Auto Close Tags",
          "Close HTML/XML tags when </ is typed.", True),
        b("match_brackets", "Match Brackets",
          "Underline brackets surrounding the caret.", True),
        b("match_brackets_content", "Match Brackets Content",
          "Only highlight when caret is next to a bracket.", True),
        b("match_brackets_square", "Match Square Brackets", "Highlight [ ] brackets.", True),
        b("match_brackets_braces", "Match Curly Braces", "Highlight { } braces.", True),
        b("match_brackets_angle", "Match Angle Brackets", "Highlight < > brackets.", False),
        b("match_tags", "Match Tags", "Highlight matching HTML/XML tag.", True),
        b("match_selection", "Match Selection",
          "Highlight other occurrences of selected text.", True),
    ]),
    ("EDITOR \u203a CARET & LINE", [
        e("caret_style", "Caret Style", "Caret animation style.", "solid",
          ["smooth", "phase", "blink", "solid"]),
        n("caret_extra_top", "Caret Extra Top", "Extra caret height above the line.", 4, step=1),
        n("caret_extra_bottom", "Caret Extra Bottom",
          "Extra caret height below the line.", 4, step=1),
        n("caret_extra_width", "Caret Extra Width", "Extra caret width.", 1, step=1),
        b("block_caret", "Block Caret", "Draw the caret as a block.", False),
        b("highlight_line", "Highlight Current Line", "Highlight any line with a caret.", False),
        b("highlight_gutter", "Highlight Gutter",
          "Highlight the gutter for caret lines.", True),
        b("highlight_line_number", "Highlight Line Number",
          "Highlight the caret's line number.", True),
        n("line_padding_top", "Line Padding Top",
          "Extra space at the top of each line (px).", 0, step=1),
        n("line_padding_bottom", "Line Padding Bottom",
          "Extra space at the bottom of each line (px).", 0, step=1),
    ]),
    ("EDITOR \u203a WHITE SPACE", [
        j("draw_white_space", "Draw White Space", "When white space is drawn.", ["selection"]),
        e("draw_unicode_white_space", "Draw Unicode White Space",
          "How non-ascii white space is drawn.", "punctuation",
          ["none", "punctuation", "all"]),
        b("draw_unicode_bidi", "Draw Unicode Bidi",
          "Draw unicode bidi characters as codepoints.", True),
        e("control_character_style", "Control Character Style",
          "How control characters are drawn.", "hex", ["hex", "names"]),
        e("selection_description_column_type", "Column Counting",
          "How the status bar counts columns.", "virtual", ["virtual", "real"]),
    ]),
    ("EDITOR \u203a SCROLLING", [
        e("scroll_past_end", "Scroll Past End",
          "Allow scrolling past the buffer end.", True, [(True, "On"), (False, "Off")]),
        n("scroll_context_lines", "Scroll Context Lines",
          "Context lines kept when scrolling to reveal.", 0, step=1),
        b("move_to_limit_on_up_down", "Move To Limit",
          "Up/down on first/last line moves to limit.", False),
        n("scroll_speed", "Scroll Speed",
          "0 disables smooth scrolling; >1 is faster.", 1.0, step=0.5, is_float=True),
    ]),
    ("EDITOR \u203a MINIMAP", [
        b("draw_minimap_border", "Minimap Border",
          "Border around the visible rectangle.", False),
        b("always_show_minimap_viewport", "Always Show Viewport",
          "Always visualise the viewport.", False),
        b("minimap_horizontal_scrolling", "Minimap Horizontal Scroll",
          "Scroll minimap horizontally.", False),
    ]),
    ("EDITOR \u203a COMPLETION", [
        b("show_definitions", "Show Definitions",
          "Popup definitions when hovering a word.", True),
        b("tab_completion", "Tab Completion",
          "Tab inserts the best matching completion.", True),
        b("auto_complete", "Auto Complete", "Trigger auto complete while typing.", True),
        n("auto_complete_size_limit", "Auto Complete Size Limit",
          "Max file size for auto trigger (bytes).", 4194304, step=1048576),
        n("auto_complete_delay", "Auto Complete Delay",
          "Delay before the popup shows (ms).", 50, step=10),
        s("auto_complete_selector", "Auto Complete Selector",
          "Scopes where auto complete triggers.",
          "meta.tag, source - comment - string.quoted.double.block"
          " - string.quoted.single.block - string.unquoted.heredoc"),
        j("auto_complete_triggers", "Auto Complete Triggers",
          "Extra situations that trigger completion.",
          [{"selector": "text.html, text.xml", "characters": "<"},
           {"selector": "punctuation.accessor", "rhs_empty": True}]),
        b("auto_complete_commit_on_tab", "Commit On Tab",
          "Commit completion on tab instead of enter.", False),
        b("auto_complete_with_fields", "Complete With Fields",
          "Show completions while snippet fields are active.", False),
        b("auto_complete_cycle", "Auto Complete Cycle",
          "Wrap selection at the ends of the list.", False),
        b("auto_complete_use_index", "Use Index",
          "Use indexed data for completions.", True),
        b("auto_complete_use_history", "Use History",
          "Auto-select previously chosen completions.", False),
        e("auto_complete_preserve_order", "Preserve Order",
          "How results reorder while typing.", "some", ["none", "some", "strict"]),
        b("auto_complete_trailing_symbols", "Trailing Symbols",
          "Add trailing symbols when likely.", False),
        b("auto_complete_trailing_spaces", "Trailing Spaces",
          "Add a trailing space when likely.", True),
        b("auto_complete_include_snippets", "Include Snippets",
          "Include snippets in auto complete.", True),
        b("auto_complete_include_snippets_when_typing", "Snippets While Typing",
          "Show snippets while typing.", True),
        n("syntax_detection_size_limit", "Syntax Detection Limit",
          "Max file size for syntax detection (bytes).", 16777216, step=1048576),
        j("ignored_snippets", "Ignored Snippets",
          "Wildcard patterns of snippets to ignore.", []),
    ]),
    ("EDITOR \u203a FIND", [
        b("copy_with_empty_selection", "Copy Empty Selection",
          "Copy/cut the current line when nothing selected.", True),
        b("find_selected_text", "Find Selected Text",
          "Copy selection into the find panel.", True),
        b("regex_auto_escape", "Regex Auto Escape",
          "Auto-escape pasted text in regex search.", True),
        e("auto_find_in_selection", "Auto Find In Selection",
          "Enable \"in selection\" for multi-line selections.", False,
          [(False, "Off"), (True, "On"), ("find_only", "Find Only"),
           ("replace_only", "Replace Only")]),
        b("close_find_after_find_all", "Close After Find All",
          "Close find panel after Find All.", True),
        b("close_find_after_replace_all", "Close After Replace All",
          "Close find panel after Replace All.", True),
        b("highlight_find_results_in_scrollbar", "Highlight In Scrollbar",
          "Highlight find results in the scrollbar.", True),
        n("find_scroll_highlights_limit", "Scroll Highlight Limit",
          "Max results shown in the scrollbar (0 = no limit).", 8192, step=512),
        n("find_highlight_matches_max_size", "Highlight Matches Max Size",
          "Max file size for highlight matches (bytes).", 16777216, step=1048576),
        n("find_regex_highlight_matches_max_size", "Regex Highlight Max Size",
          "As above, for regex (bytes).", 1048576, step=1048576),
        n("find_in_files_max_result_size", "Find-In-Files Result Size",
          "Max output size for find in files (bytes).", 16777216, step=1048576),
        b("find_in_files_side_by_side", "Find-In-Files Side By Side",
          "Open results side-by-side.", False),
        n("find_in_files_context_lines", "Find-In-Files Context Lines",
          "Context lines per result.", 2, step=1),
        n("find_in_files_context_characters", "Context Characters",
          "Surrounding characters per result (0 = no limit).", 300, step=50),
        b("find_in_files_suppress_errors", "Suppress Errors",
          "Hide file open/search errors in results.", False),
        n("find_in_files_max_file_size", "Find-In-Files Max File",
          "Skip files larger than this (bytes).", 104857600, step=1048576),
        b("drag_text", "Drag Text", "Click selected text to drag-drop it.", True),
        b("focus_on_file_drop", "Focus On File Drop",
          "Take focus when a file is dropped in.", False),
    ]),
    ("STATUS BAR", [
        b("show_git_status_in_status_bar", "Git Status",
          "Show git status in the status bar.", True),
        b("show_encoding", "Encoding", "Show file encoding.", False),
        b("show_line_endings", "Line Endings", "Show line endings.", False),
        b("show_indentation", "Indentation", "Show indentation.", True),
        b("show_syntax", "Syntax", "Show syntax.", True),
        e("show_line_column", "Line / Column", "Show Line, Column readout.", "enabled",
          ["enabled", "compact", "disabled"]),
        b("show_spelling_errors", "Spelling Errors", "Show misspelled word count.", True),
    ]),
    ("EDITOR \u203a SPELL CHECK", [
        b("spell_check", "Spell Check", "Turn spell checking on by default.", False),
        s("dictionary", "Dictionary", "Word list used for spell checking.",
          "Packages/Language - English/en_US.dic"),
        s("spelling_selector", "Spelling Selector", "Scopes checked for spelling errors.",
          "markup.raw, source string.quoted - punctuation"
          " - meta.preprocessor.include, source comment"
          " - source comment.block.preprocessor,"
          " -(source, constant, keyword, storage, support, variable,"
          " markup.underline.link, meta.tag)"),
    ]),
    ("EDITOR \u203a WORDS", [
        s("word_separators", "Word Separators", "Characters that separate words.",
          "./\\()\"'-:,.;<>~!@#$%^&*|+=[]{}`~?"),
        s("sub_word_separators", "Sub-word Separators",
          "Characters that separate sub-words.", "_"),
    ]),
    ("FILES \u203a SAVE", [
        e("trim_trailing_white_space_on_save", "Trim Trailing White Space",
          "Trim trailing whitespace on save.", "none", ["none", "all", "not_on_caret"]),
        b("trim_only_modified_white_space", "Trim Only Modified",
          "Only trim whitespace you modified.", True),
        b("ensure_newline_at_eof_on_save", "Newline At EOF",
          "Ensure a trailing newline on save.", False),
        b("save_on_focus_lost", "Save On Focus Lost", "Auto-save when switching away.", False),
    ]),
    ("FILES \u203a ENCODING", [
        s("fallback_encoding", "Fallback Encoding",
          "Used when encoding can't be detected.", "Western (Windows 1252)"),
        s("default_encoding", "Default Encoding",
          "Encoding for new/undefined files.", "UTF-8"),
        b("enable_hexadecimal_encoding", "Hex For Null Bytes",
          "Open files with null bytes as hex.", True),
        e("default_line_ending", "Default Line Ending",
          "Line terminator for new files.", "system", ["system", "windows", "unix"]),
    ]),
    ("UI \u203a AUTO HIDE", [
        b("auto_hide_menu", "Auto Hide Menu", "Hide the menu while typing.", False),
        b("auto_hide_tabs", "Auto Hide Tabs", "Hide tabs while typing.", False),
        b("auto_hide_status_bar", "Auto Hide Status Bar",
          "Hide the status bar while typing.", False),
        b("reveal_tabs_with_timeout", "Reveal Tabs Briefly",
          "Briefly show tabs when switching files.", False),
        b("reveal_menu", "Reveal Menu (alt)", "Alt taps reveal the menu (Win/Linux).", True),
        b("hide_pointer_while_typing", "Hide Pointer While Typing",
          "Hide the mouse pointer while typing.", True),
    ]),
    ("APPLICATION \u203a BEHAVIOR", [
        e("hot_exit", "Hot Exit", "Preserve unsaved state on exit.", "always",
          ["always", "only_on_quit", "disabled"]),
        b("hot_exit_projects", "Hot Exit Projects",
          "Close projects without prompting.", True),
        b("remember_full_screen", "Remember Full Screen", "Reopen in full screen.", False),
        b("remember_workspace", "Remember Workspace",
          "Remember each window's workspace.", True),
        b("remember_layout", "Remember Layout",
          "Reopen with the same layout (hot_exit off).", False),
        b("update_system_recent_files", "Update Recent Files",
          "Update the OS recent files list.", True),
        b("shell_environment", "Shell Environment (Mac)",
          "Load the user's shell env. Needs restart.", True),
        b("reload_file_on_change", "Reload On Change",
          "Reload files changed on disk.", True),
        b("always_prompt_for_file_reload", "Always Prompt On Reload",
          "Prompt even for unmodified files.", False),
        b("reload_file_in_background", "Reload In Background",
          "Reload while ST is not focused.", False),
        b("close_deleted_files", "Close Deleted Files",
          "Close saved files deleted from disk.", True),
        e("open_files_in_new_window", "Open In New Window",
          "When externally opening files.", "never",
          ["never", "always", "finder_only"]),
        b("create_window_at_startup", "Window At Startup (Mac)",
          "Create an empty window at startup.", True),
        b("show_navigation_bar", "Touch Bar Recents (Mac)",
          "Show recent files on the Touch Bar.", True),
        b("use_find_clipboard", "Find Clipboard (Mac)",
          "Use the global find clipboard.", True),
        b("close_windows_when_empty", "Close Empty Windows",
          "Close a window when its last file closes.", False),
        b("show_full_path", "Show Full Path",
          "Show full file path in the title bar.", True),
        b("show_rel_path", "Show Relative Path",
          "Show relative path for sidebar files.", False),
        b("show_project_first", "Project First",
          "Show \"project - file\" order.", False),
        b("show_panel_on_build", "Panel On Build",
          "Show build results when building.", True),
        b("show_errors_inline", "Errors Inline",
          "Show build errors under their line.", True),
        b("show_git_status", "Git Status (restart)",
          "Show git status. Needs restart.", True),
        b("allow_git_home_dir", "Allow Git Home Dir",
          "Show git status for the home directory.", False),
        e("git_diff_target", "Git Diff Target",
          "Diff tracked files against index or HEAD.", "index", ["index", "head"]),
        s("sublime_merge_path", "Sublime Merge Path",
          "Path to Sublime Merge (empty = auto).", ""),
        e("preview_on_click", "Preview On Click", "Preview sidebar files on click.", True,
          [(True, "On"), (False, "Off"), ("only_left", "Only Left")]),
        b("select_across_groups", "Select Across Groups",
          "Select already-open files in any group.", False),
        n("console_max_history_lines", "Console History Lines",
          "Max lines kept in the console (0 = no limit).", 3000, step=500),
    ]),
    ("FILES \u203a INDEXING & SIDEBAR", [
        j("folder_exclude_patterns", "Folder Exclude Patterns",
          "Folders hidden from the sidebar.",
          [".svn", ".git", ".hg", "CVS", ".Trash", ".Trash-*"]),
        j("file_exclude_patterns", "File Exclude Patterns",
          "Files hidden from the sidebar.",
          ["*.pyc", "*.pyo", "*.exe", "*.dll", "*.obj", "*.o", "*.a", "*.lib",
           "*.so", "*.dylib", "*.ncb", "*.sdf", "*.suo", "*.pdb", "*.idb",
           ".DS_Store", ".directory", "desktop.ini", "*.class", "*.psd", "*.db",
           "*.sublime-workspace"]),
        j("binary_file_patterns", "Binary File Patterns",
          "Shown in sidebar but excluded from Goto/Find.",
          ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.ttf", "*.tga", "*.dds", "*.ico",
           "*.eot", "*.pdf", "*.swf", "*.jar", "*.zip"]),
        j("image_file_patterns", "Image File Patterns", "Files opened as images.",
          ["*.jpeg", "*.jpg", "*.gif", "*.png", "*.ico", "*.bmp", "*.tga",
           "*.psd", "*.ppm", "*.pgm", "*.webp", "*.hdr"]),
        b("index_files", "Index Files", "Build a symbol index (Goto Definition).", True),
        n("index_workers", "Index Workers",
          "Threads for indexing (0 = guess). Needs restart.", 0, step=1),
        b("index_exclude_gitignore", "Index Excludes Gitignore",
          "Skip files ignored by git.", True),
        b("index_skip_unknown_extensions", "Skip Unknown Extensions",
          "Skip unrecognised extensions.", True),
        j("index_exclude_patterns", "Index Exclude Patterns",
          "Files that won't be indexed.", ["*.log"]),
        b("goto_anything_exclude_gitignore", "Goto Excludes Gitignore",
          "Exclude git-ignored files from Goto.", False),
        b("goto_anything_file_preview", "Goto File Preview",
          "Preview file contents in Goto Anything.", True),
    ]),
    ("PACKAGES \u203a VINTAGE", [
        b("vintage_start_in_command_mode", "Start In Command Mode",
          "Open files in command mode.", False),
        b("vintage_use_clipboard", "Use Clipboard",
          "Yank to the system clipboard.", False),
        b("vintage_ctrl_keys", "Ctrl Keys",
          "Make ctrl keys behave like vim.", False),
        j("ignored_packages", "Ignored Packages",
          "Packages to ignore. May need restart.", ["Vintage"]),
    ]),
]

# Flat lookup: setting key → entry dict.
KEY_INDEX: dict = {}
for _section_title, _section_entries in SECTIONS:
    for _entry in _section_entries:
        KEY_INDEX[_entry["key"]] = _entry


# ---------------------------------------------------------------------------
# Pure HTML / string utilities
# ---------------------------------------------------------------------------

def esc(t) -> str:
    """HTML-escape a value."""
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def short(t, limit: int) -> str:
    """Truncate a string to *limit* chars, appending an ellipsis if needed."""
    t = str(t)
    return t if len(t) <= limit else t[:limit - 1] + "\u2026"


def norm_choices(entry) -> list:
    """Normalise choices to a list of (value, label) tuples."""
    return [c if isinstance(c, tuple) else (c, str(c)) for c in entry["choices"]]
