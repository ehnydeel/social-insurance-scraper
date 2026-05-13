from lxml import etree

class XmlParser:
    def parse(self, path):
        tree = etree.parse(path)
        root = tree.getroot()
        return root