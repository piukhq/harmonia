from xml.dom import minidom
from xml.dom.minidom import Node


def _remove_blanks(node: Node):
    for x in node.childNodes:
        if x.nodeType == Node.TEXT_NODE:
            if x.nodeValue:
                x.nodeValue = x.nodeValue.strip()
        elif x.nodeType == Node.ELEMENT_NODE:
            _remove_blanks(x)


def minify(xml_string: str) -> str:
    el = minidom.parseString(xml_string).documentElement
    _remove_blanks(el)
    return el.toxml().strip()
