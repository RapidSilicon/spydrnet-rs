from spydrnet.ir import Netlist, Library, Definition


class DefaultNamespace:
    @staticmethod
    def is_compliant(element):
        """
        is_compliant means that the naming of the element is a valid name and that there are no namespace conflicts
        among its children
        :param element:
        :return:
        """
        if DefaultNamespace.is_name_of_element_valid(element) and DefaultNamespace.no_name_conflicts(element):
            return True
        return False

    @staticmethod
    def is_name_of_element_valid(element):
        """
        All names are valid in the default namespace. Always returns true.
        :param element:
        :return: True
        """
        return True

    @staticmethod
    def is_name_valid(key, value):
        return True

    @staticmethod
    def no_name_conflicts(element):
        """
        Check to see if there are any name conflicts among the children
        :param element:
        :return:
        """
        namespace = set()
        if isinstance(element, Netlist):
            for library in element.libraries:
                if ".NAME" in library:
                    name = library[".NAME"]
                    if name not in namespace:
                        namespace.add(name)
                    else:
                        return False
        elif isinstance(element, Library):
            for definition in element.definitions:
                if ".NAME" in definition:
                    name = definition[".NAME"]
                    if name not in namespace:
                        namespace.add(name)
                    else:
                        return False
        elif isinstance(element, Definition):
            for port in element.ports:
                if ".NAME" in port:
                    name = port[".NAME"]
                    if name not in namespace:
                        namespace.add(name)
                    else:
                        return False
            namespace.clear()
            for cable in element.cables:
                if ".NAME" in cable:
                    name = cable[".NAME"]
                    if name not in namespace:
                        namespace.add(name)
                    else:
                        return False
            namespace.clear()
            for instance in element.children:
                if ".NAME" in instance:
                    name = instance[".NAME"]
                    if name not in namespace:
                        namespace.add(name)
                    else:
                        return False
        return True

    @staticmethod
    def needs_namespace(element):
        if isinstance(element, (Netlist, Library, Definition)):
            return True
        return False

    def __init__(self):
        self.namespaces = dict()

    def no_conflict(self, element, key, value):
        if key != ".NAME":
            return True
        element_type = type(element)
        if element_type in self.namespaces:
            namespace = self.namespaces[element_type]
            if value in namespace:
                if namespace[value] != element:
                    return False
        return True

    def update(self, element, key, value):
        if key == ".NAME":
            element_type = type(element)
            if element_type not in self.namespaces:
                self.namespaces[element_type] = dict()
            namespace = self.namespaces[element_type]
            if ".NAME" in element:
                old_name = element[".NAME"]
                if old_name in namespace:
                    del namespace[old_name]
            namespace[value] = element

    def remove(self, element, key):
        if key == ".NAME":
            element_type = type(element)
            if element_type in self.namespaces:
                namespace = self.namespaces[element_type]
                if ".NAME" in element:
                    old_name = element[".NAME"]
                    if old_name in namespace:
                        del namespace[old_name]
