from enforce_typing import enforce_types
import numpy


@enforce_types
class BlockRange:
    def __init__(self, st: int, fin: int, num_samples: int, random_seed=None):
        """
        @arguments
          st -- start block
          fin -- end block
          num_samples -- # blocks to randomly sample from (without replacement)
          random_seed -- pass in an integer for predictable sampling
        """
        assert st >= 0
        assert fin > 0
        assert num_samples >= 0
        assert st <= fin

        self.st: int = st
        self.fin: int = fin

        if num_samples == 0:
            self._blocks = []
            return

        cand_blocks = list(range(st, fin))  # [)

        # num_samples-1 because we include fin at the end
        num_samples = min(num_samples - 1, len(cand_blocks))
        if random_seed is not None:
            numpy.random.seed(random_seed)

        self._blocks = sorted(
            numpy.random.choice(cand_blocks, num_samples, replace=False)
        )

        if fin not in self._blocks:
            # always include the last block
            self._blocks.append(fin)

    def getBlocks(self) -> list:
        return self._blocks

    def numBlocks(self) -> int:
        return len(self.getBlocks())

    def filterByMaxBlock(self, max_block: int):
        """
        @arguments
          max_block -- maximum block number to include in the range
        """
        new_blocks = []
        for b in self.getBlocks():
            if b <= max_block:
                new_blocks.append(b)

        self._blocks = new_blocks

    def __str__(self):
        return (
            f"BlockRange: st={self.st}, fin={self.fin}"
            f", # blocks sampled={self.numBlocks()}"
            f", range={self.getBlocks()[:4]}.."
        )
