import os


class Buf:
    """Strict/lazy buffer"""
    path = None # abs path to the file
    lazy = False
    data = None # file content
    name = None # only name of the file

    def __init__(self, path, lazy=False):
        """If `lazy` loads it on each demand, and does not cache it"""
        self.path = path
        self.name = os.path.basename(self.path)
        self.lazy = lazy
        if not self.lazy:
            with open(self.path, 'rb') as f:
                self.data = f.read()

    def get_data(self):
        if self.lazy:
            with open(self.path, 'rb') as f:
                return f.read()
        else:
            return self.data


#################################################################################################################
class Attachments:
    bufs = {}

    def __init__(self, path, lazy=False):
        self.bufs = {}
        if os.path.exists(path):
            for att_name in os.listdir(path):
                att_path = os.path.join(path, att_name)
                self.bufs[att_path] = Buf(att_path, lazy)

    # def get_data(self, path):
        # return self.bufs[path].get_data()

    def merge(self, other):
        self.bufs.update(other.bufs)

    def items(self):
        return ((b.name, b.get_data()) for b in self.bufs.values())