import re

def tent_name_list_dict_sorting(s):
    """Helper for natural sorting (e.g., 2 before 10, '71-1' before '71-2')."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]
