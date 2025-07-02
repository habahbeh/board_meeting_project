from django import template

register = template.Library()


@register.filter
def dictsortby(value, arg):
    """
    فرز قائمة بناءً على مفتاح محدد
    """
    return sorted(value, key=lambda x: getattr(x, arg))


@register.filter
def regroup_by(value, arg):
    """
    تجميع القائمة بناءً على مفتاح محدد
    مثال: is_decision:True
    """
    field, value_str = arg.split(':')
    value_bool = value_str.lower() == 'true'

    result = []
    for item in value:
        if getattr(item, field) == value_bool:
            result.append(item)

    return result