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
    processFunc = (lambda s: " ".join(s.split())) or (lambda s: s)
    for method in methodList:
        try:
            m_desc = processFunc(str(getattr(object, method).__doc__))
            # print(str(method.ljust(spacing)) + " " + m_desc)
            if m_desc is not None and m_desc != "None" and not m_desc.startswith("__"):
                methods[method] = m_desc
        except Exception:
            print(method.ljust(spacing) + " " + " getattr() failed")
    return methods
