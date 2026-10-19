"""Conservative native Accessibility hit-test policy, independent of model labels."""
def safe_target(role,ancestors):
    # Browser documents can attach side effects to arbitrary elements. Native
    # navigation is only accepted outside web content and without missing ancestry.
    if not ancestors or 'AXWebArea' in ancestors:return False
    if role in ('AXTextField','AXTextArea','AXScrollBar','AXSplitter','AXMenuBarItem','AXDisclosureTriangle'):
        return True
    return role=='AXRadioButton' and ancestors[0]=='AXTabGroup'
