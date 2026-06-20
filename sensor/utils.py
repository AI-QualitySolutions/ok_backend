def check_arafat(input_string):
    if '-' in input_string:
        substring = input_string.split('-')[1]
        return substring.strip().lower() == "arafat"
    else:
        return False

def get_string_before_dash(input_string):
    if '-' in input_string:
        return input_string.split('-')[0]
    else:
        return input_string