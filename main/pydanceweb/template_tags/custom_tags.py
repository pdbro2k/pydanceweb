from django.template.defaulttags import register

@register.filter
def get_item(dictionary, key):
    key = str(key)
    if key in dictionary:
        return dictionary[str(key)]
    return ""
