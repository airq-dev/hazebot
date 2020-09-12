import typing


T = typing.TypeVar("T")


class TrieNode(typing.Generic[T]):
    def __init__(self):
        self.values: typing.List[T] = []
        self.children: typing.Dict[str, TrieNode] = {}


class Trie(typing.Generic[T]):
    """A simple in-memory trie"""

    def __init__(self):
        self._root: TrieNode[T] = TrieNode()

    def insert(self, key: str, value: T):
        curr = self._root
        for c in key:
            if c not in curr.children:
                node: TrieNode[T] = TrieNode()
                curr.children[c] = node
            curr = curr.children[c]
        curr.values.append(value)

    def get(self, prefix: str) -> typing.List[T]:
        curr = self._root
        for c in prefix:
            curr = curr.children.get(c, TrieNode())
        results = []
        stack = [curr]
        while stack:
            curr = stack.pop()
            results.extend(curr.values)
            stack.extend(curr.children.values())
        return results
