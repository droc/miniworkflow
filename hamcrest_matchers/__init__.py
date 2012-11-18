from hamcrest.core.base_matcher import BaseMatcher
from hamcrest.core.helpers.hasmethod import hasmethod

class responds_to(BaseMatcher):
    def __init__(self, method):
        self.method = method

    def _matches(self, item):
        return hasmethod(item, self.method)

    def describe_mismatch(self, item, mismatch_description):
        mismatch_description.append("Expected %s to respond to %s" % (item, self.method))