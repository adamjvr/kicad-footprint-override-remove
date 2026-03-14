#!/usr/bin/env python3
"""
remove_pad_soldermask_overrides.py

Author: ChatGPT
Purpose:
--------
This script processes a single KiCad footprint file (.kicad_mod) and removes
all pad-level solder mask overrides.

Specifically, it removes any expression of the form:

    (solder_mask_margin <value>)

that appears inside a pad definition.

Example pad BEFORE cleaning:

    (pad "1" smd rect
      (at 0 0)
      (size 1 1)
      (layers "F.Cu" "F.Mask")
      (solder_mask_margin 0.05)
    )

Example pad AFTER cleaning:

    (pad "1" smd rect
      (at 0 0)
      (size 1 1)
      (layers "F.Cu" "F.Mask")
    )

Why this script exists
----------------------
In KiCad footprints, pads can override the global solder mask clearance by
including a `(solder_mask_margin ...)` expression. When building libraries or
cleaning vendor footprints, it is often desirable to remove these overrides
so that the board-level design rules control mask expansion.

This script safely removes those overrides without damaging the rest of the
footprint structure.

Important design notes
----------------------
KiCad files are S-expression formatted text files.

Example:

    (pad "1" smd rect
        (at 0 0)
        (size 1 1)
    )

Because parentheses determine structure, we cannot blindly use regex to
remove text. Instead, this script performs a **simple structural parse**
that keeps track of parentheses depth so we know exactly where pad blocks
begin and end.

This avoids corrupting the footprint file.

Usage
-----

Overwrite file in place:

    python remove_pad_soldermask_overrides.py footprint.kicad_mod

Write output to new file:

    python remove_pad_soldermask_overrides.py footprint.kicad_mod cleaned.kicad_mod
"""

import sys
import re


# -----------------------------------------------------------------------------
# FUNCTION: find_matching_paren
# -----------------------------------------------------------------------------
def find_matching_paren(text, start_index):
    """
    Locate the closing parenthesis that matches the opening parenthesis
    at start_index.

    KiCad files use nested parentheses extensively, so we must track the
    nesting depth to find the correct matching parenthesis.

    Example:

        (pad
            (size 1 1)
            (layers "F.Cu")
        )

    The pad block begins at '(' and ends at the final ')'.

    Parameters
    ----------
    text : str
        Entire text of the KiCad file.

    start_index : int
        Index where the opening '(' occurs.

    Returns
    -------
    int
        Index of the matching closing ')'.

    Raises
    ------
    ValueError
        If no matching closing parenthesis is found.
    """

    depth = 0

    # Iterate through the file starting from the opening parenthesis
    for i in range(start_index, len(text)):

        char = text[i]

        # Opening parenthesis increases nesting depth
        if char == "(":
            depth += 1

        # Closing parenthesis decreases nesting depth
        elif char == ")":
            depth -= 1

            # When depth returns to zero we have matched the original '('
            if depth == 0:
                return i

    # If we reach the end of the file without depth reaching zero
    raise ValueError("Matching closing parenthesis not found.")


# -----------------------------------------------------------------------------
# FUNCTION: remove_soldermask_override
# -----------------------------------------------------------------------------
def remove_soldermask_override(pad_block):
    """
    Remove solder mask override expressions from a pad block.

    Specifically removes any expression matching:

        (solder_mask_margin <number>)

    Example removal:

        (solder_mask_margin 0.05)
        (solder_mask_margin -0.01)
        (solder_mask_margin 0)

    Parameters
    ----------
    pad_block : str
        Text containing the entire pad block.

    Returns
    -------
    str
        Pad block with solder mask overrides removed.
    """

    # Regex pattern explanation:
    #
    # \(                     literal "("
    # solder_mask_margin     exact keyword
    # \s+                    whitespace
    # [-0-9.]+               numeric value (can include minus or decimal)
    # \)                     closing parenthesis
    #
    pattern = r"\(solder_mask_margin\s+[-0-9.]+\)"

    # Replace the override with nothing (delete it)
    cleaned_pad = re.sub(pattern, "", pad_block)

    return cleaned_pad


# -----------------------------------------------------------------------------
# FUNCTION: process_footprint
# -----------------------------------------------------------------------------
def process_footprint(text):
    """
    Scan the footprint file, locate every pad block, and remove
    solder mask overrides from them.

    This function reconstructs the entire file while modifying only
    pad blocks.

    Parameters
    ----------
    text : str
        Full text of the KiCad footprint file.

    Returns
    -------
    str
        Cleaned footprint text.
    """

    output = []
    cursor = 0

    while True:

        # Find the next pad definition
        pad_index = text.find("(pad", cursor)

        # If no more pads exist, append remaining file and stop
        if pad_index == -1:
            output.append(text[cursor:])
            break

        # Copy everything before this pad unchanged
        output.append(text[cursor:pad_index])

        # Determine the full pad block boundaries
        pad_end = find_matching_paren(text, pad_index)

        pad_block = text[pad_index:pad_end + 1]

        # Remove solder mask overrides from this pad
        cleaned_pad = remove_soldermask_override(pad_block)

        # Append cleaned pad block
        output.append(cleaned_pad)

        # Move cursor forward
        cursor = pad_end + 1

    # Reassemble entire footprint text
    return "".join(output)


# -----------------------------------------------------------------------------
# MAIN PROGRAM
# -----------------------------------------------------------------------------
def main():
    """
    Main program logic.

    Handles:
        - Argument parsing
        - File reading
        - Processing
        - File writing
    """

    # Validate arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python remove_pad_soldermask_overrides.py input.kicad_mod [output.kicad_mod]")
        sys.exit(1)

    input_file = sys.argv[1]

    # If output path not specified, overwrite input file
    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        output_file = input_file

    # -------------------------------------------------------------------------
    # Read footprint file
    # -------------------------------------------------------------------------
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            footprint_text = f.read()
    except Exception as e:
        print("Error reading file:", e)
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Process footprint
    # -------------------------------------------------------------------------
    cleaned_text = process_footprint(footprint_text)

    # -------------------------------------------------------------------------
    # Write cleaned footprint
    # -------------------------------------------------------------------------
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
    except Exception as e:
        print("Error writing file:", e)
        sys.exit(1)

    print("Finished cleaning footprint.")
    print("Input file :", input_file)
    print("Output file:", output_file)


# -----------------------------------------------------------------------------
# Script Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
