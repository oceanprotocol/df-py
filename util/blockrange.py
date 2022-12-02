import sys
import numpy
from enforce_typing import enforce_types
from util.blocktime import getstfinBlocks


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

        cand_blocks = list(range(st, fin + 1))  # []

        if num_samples == 1:
            print("WARNING: num_samples=1, so not sampling")
            self._blocks = [fin]
            return

        num_samples = min(num_samples, len(cand_blocks))
        if random_seed is not None:
            numpy.random.seed(random_seed)

        self._blocks = sorted(
            numpy.random.choice(cand_blocks, num_samples, replace=False)
        )

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


def create_range(chain, st, fin, samples, rndseed) -> BlockRange:
    if st == "api" or fin == "api":
        print("dfblocks has been deprecated")
        sys.exit()

    st_block, fin_block = getstfinBlocks(chain, st, fin)
    rng = BlockRange(st_block, fin_block, samples, rndseed)
    rng.filterByMaxBlock(len(chain) - 5)

    return rng
