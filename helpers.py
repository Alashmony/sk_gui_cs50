# import json
import inspect


def get_methods(object):
    """Gets all methods for a certain type, returns a dictionary of methods and their description

    Args:
        object (_type_): _description_
    """
    methodList = []
    spacing = 0
    methods = {}
    for method_name in dir(object):
        try:
            if callable(getattr(object, method_name)):
                methodList.append(str(method_name))
                spacing = max(spacing, len(method_name))
        except Exception:
            methodList.append(str(method_name))
    # processFunc = (lambda s: " ".join(s.split())) or (lambda s: s)
    for method in methodList:
        try:
            m_desc = getattr(object, method).__doc__
            m_args = list(inspect.signature(getattr(object, method)).parameters.keys())

            # print(str(method.ljust(spacing)) + " " + m_desc)
            if m_desc is not None and m_desc != "None" and not method.startswith("_"):
                methods[method] = {}
                methods[method]["args"] = m_args
                methods[method]["description"] = m_desc
        except Exception as e:
            print(method.ljust(spacing) + " " + str(e) + " failed")
    return methods
